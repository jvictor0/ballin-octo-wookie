# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import _mysql
import itertools
import time
import sys
import collections

def ConnectToMySQL(host=None, port=3307, user='root', database='', **kwargs):
    if not host:
        host = '%s:%s' % ("127.0.0.1", port)
    db = Connection(host=host, user=user, database=database, **kwargs)
    return db

class Connection(object):
    def __init__(self, host, user, database):

        sys_vars = dict(
                character_set_server =  "utf8mb4",
                collation_server =      "utf8mb4_unicode_ci",)

        sys_vars["sql_mode"] = "STRICT_ALL_TABLES"
        args = dict(db=database, local_infile=1)

        from MySQLdb.converters import conversions

        args["user"] = user

        self.socket = None
        pair = host.split(":")
        if len(pair) == 2:
            args["host"] = pair[0]
            args["port"] = int(pair[1])
        else:
            args["host"] = host
            args["port"] = 3306
        self.port = args["port"]

        args["connect_timeout"] = 10
        args["init_command"] = 'set names "utf8mb4" collate "utf8mb4_bin"' + ''.join([', @@%s = "%s"' % t for t in sys_vars.items()])

        self._db = None
        self._db_args = args
        self.encoders = dict([ (k, v) for k, v in conversions.items()
                               if type(k) is not int ])
        self._last_use_time = time.time()
        self.reconnect()
        self._db.set_character_set("utf8")

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def set_print_queries(self, print_queries):
        self.print_queries = print_queries

    def close(self):
        """Closes this database connection."""
        if getattr(self, "_db", None) is not None:
            self._db.close()
            self._db = None

    def reconnect(self):
        """Closes the existing database connection and re-opens it."""
        conn = _mysql.connect(**self._db_args)
        if conn is not None:
            self.close()
            self._db = conn

    def query(self, query, *parameters):
        self._execute(query, *parameters)
        self._result = self._db.use_result()
        if self._result is None:
            return self._rowcount
        fields = zip(*self._result.describe())[0]
        rows = list(self._result.fetch_row(0))
        ret = SelectResult(fields, rows)
        return ret;

    def affected_rows(self):
        return self._rowcount

    def get(self, query, *parameters):
        """Returns the first row returned for the given query."""
        rows = self.query(query, *parameters)
        if not rows:
            return None
        elif not isinstance(rows, list):
            raise Exception("Query is not a select query")
        elif len(rows) > 1:
            raise Exception("Multiple rows returned for Database.get() query")
        else:
            return rows[0]


    def execute(self, query, *parameters):
        """Executes the given query, returning the lastrowid from the query."""
        return self.execute_lastrowid(query, *parameters)

    def execute_lastrowid(self, query, *parameters):
        """Executes the given query, returning the lastrowid from the query."""
        self._execute(query, *parameters)
        self._result = self._db.store_result()
        return self._db.insert_id()

    def execute_rowcount(self, query, *parameters):
        """Executes the given query, returning the rowcount from the query."""
        self._execute(query, *parameters)
        self._result = self._db.store_result()
        return self._result.num_rows()

    def _execute(self, query, *parameters):
        if parameters != None and parameters != ():
            query = query % tuple([self._db.escape(p, self.encoders) for p in parameters])
        if isinstance(query, unicode):
            query = query.encode(self._db.character_set_name())
        self._db.query(query)
        self._rowcount = self._db.affected_rows()


from collections import OrderedDict
class Row(OrderedDict):
    """A dict that allows for object-like property access syntax."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __hash__(self):
        return hash(tuple(sorted(self.iteritems())))


class SelectResult(list):
    """ Goal: create a container to hold a sql result that doesn't lose any
        information, but is compatable with our current scripts """
    def __init__(self, fieldnames, values, format="dict"):
        self.fieldnames = fieldnames
        self.values = values
        self.format = format

    def __iter__(self):
        if self.format == "dict":
            return iter(self.old_format())
        else:
            return iter(self.values)

    def __len__(self):
        return len(self.values)

    def width(self):
        return len(self.fieldnames)

    def __getitem__(self, rowId):
        if isinstance(rowId, slice):
            return SelectResult(self.fieldnames, self.values[rowId], self.format);
        elif self.format == "dict":
            return Row(zip(self.fieldnames, self.values[rowId]))
        else:
            return self.values[rowId]

    def __eq__(self, other):
        # don't use isinstance here because this class inherits list
        if type(other)==list:
            # remain compatible with old tests
            return other == self.old_format()
        return results_equal(self, other, True)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return str(self.old_format())

    def __repr__(self):
        return str(self)

    def sort(self):
        self.values.sort()

    def old_format(self):
        return [Row(itertools.izip(self.fieldnames, row)) for row in self.values]

    def filter_columns(self, keys):
        ikeys = [key for key in keys if isinstance(key, int)]
        skeys = [key for key in keys if isinstance(key, str)]
        selection = [i for i in range(self.width()) if i in ikeys or self.fieldnames[i] in skeys]
        return SelectResult([self.fieldnames[i] for i in selection],
                [[value[i] for i in selection] for value in self.values], self.format)

    def set_format(self, format):
        self.format = format

    def format_column(self, value):
        if value is None:
            return "NULL"
        if type(value) == "date":
            return value.isoformat()
        if type(value) == "datetime":
            return value.isoformat()
        return str(value)

    def format_assoc(self):
        return [", ".join(["%s:%s" % (col[0], self.format_column(col[1])) for col in zip(self.fieldnames, row)]) for row in self.values]

    def format_table(self, return_list=False):
        if len(self) == 0:
            ret = ["Empty Set"]
        else:
            values = [[self.format_column(column) for column in row] for row in self.values]
            widths = [max(len(self.fieldnames[i]), max([len(row[i]) for row in values])) for i in xrange(len(self.fieldnames))]

            separator = '+' + ''.join(['-' * (width+2) + '+' for width in widths])
            format_string  = "| " + " | ".join(["{%d:%d}" % (i, widths[i])
                                        for i in range(len(widths))]) + " |"
            footer = "%d row%s in set" % (len(values), "" if len(values) == 1 else "s")

            ret  = [separator]
            ret += [format_string.format(*self.fieldnames)]
            ret += [separator]
            ret += [format_string.format(*row) for row in values]
            ret += [separator]
            ret += [footer]

        if return_list:
            return ret
        return '\n'.join(ret)
