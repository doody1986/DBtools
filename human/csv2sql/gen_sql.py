#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  csv2xsd.py
#  4/1/2015
#  Copyright 2015 leiming <ylm@ece.neu.edu>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#


## Warnings: If the input structure changes, e.g. the redcap template, the
##          following code needs to be changed too. For more info, please
##          contact the author.

## current layout of the template
# info[0]       :   field name
# info[1]       :   form name
# info[2]       :   section header
# info[3]       :   field type
# info[4]       :   field label
# info[5]       :   choices, calculations, labels
# info[6]       :   field note
# info[7]       :   Text Validation Type OR Show Slider Number
# info[8]       :   Text Validation Min
# info[9]       :   Text Validation Max
# info[10]      :   Identifier?
# info[11]      :   Branching Logic (Show field only if...)
# info[12]      :   Required Field?
# there are other fields, but not important

import sys
import csv
import re

#modify the field types if necessary
FieldType = ['text','radio','notes', 'checkbox']
target_table = "postpartum_data_abstraction"

# for each field type, there could be multiple specific types
# For example,
#   text        :   date, char(string)
#   radio       :   integer list
#   checkbox    :   integer list
#   notes       :   char(string)

#   text->date  :   MM-DD-YYY / hh:mm / Military Time
#   text->char  :   char(200)
#   radio->integer list :   looking for '|' as separator and extract integers
#   checkbox->integer   :   same as radio
#   notes->char :   always char, using char(200) as default


Template_No_Constraint = \
"name type null_str,\n"

Template_Constraint = \
"fieldname type null_str,\n" + \
"CONSTRAINT tablename_fieldname_CK CHECK (conditions),\n"


# the first column is the data field
# to generate the xml format, we need to know
# 1) data type  2) data range
def GenTemplate(info):
    format_string = ""
    null_str = "NULL"
    condstr = ""

    ## extract related fields
    ## branching logic is not considered here
    field_name     = info[0]        # name
    field_type     = info[3]        # data type
    field_choices  = info[5]        # data options
    field_note     = info[6]        # specific notes, such as date format
    field_valid    = info[7]
    field_min      = info[8]
    field_max      = info[9]

    # (1) change to upper case
    field_name = field_name.strip().upper()

    # (2) determine the data type
    FType = ""

    if(field_type == 'notes'):
        FType = "VARCHAR(200)"
#        FType = "string"

    if(field_type == 'radio' or field_type == 'checkbox'):
        FType = "INT"
#        FType = "integer"

    if(field_type == 'text'):
         # date
        index_date_1 = field_note.find('MM-DD-YYY')
        index_date_2 = field_note.find('MM/DD/YYY')

        # time
        index_time_1 = field_note.find('hh:mm')
        index_time_2 = field_note.find('Military Time')

        # integer
        index_int = field_valid.find('integer')

        # string
        n = 0
        if (index_date_1 > -1 or index_date_2 > -1):
            n = 1
        if (index_time_1 > -1 or index_time_2 > -1):
            n = 2
        if (index_int > -1):
            n = 3

        if n == 1:
            FType = "DATE"

        elif n == 2:
            FType = "TIME"

        elif n == 3:
            FType = "INT"

        else:
            FType = "VARCHAR(200)"



    # (3) case 1, field_choices contains options that are separated by '|'
    #     case 2, field_min and field_max have values,
    #             which excludes the time format hh:mm
    Need_Check = "no"

    # case 1
    # check "|" symbol
    sym_index = field_choices.find("|")

    if sym_index > -1:
        Need_Check = "yes"

    # case 2
    minv = field_min.strip()
    maxv = field_max.strip()
    # not empty
    if minv or maxv :
        column_1 = minv.find(":")
        column_2 = maxv.find(":")
        # exclude the time case
        if (column_1 == -1) and (column_2 == -1):
            Need_Check = "yes"


    #
    # (4) define the condition string
    #

    # extract the integers
    if sym_index > -1:
        #integer list
        list_int = []

        # extract integers out from field_choices
        sepintlist = field_choices.split('|')

        for item in sepintlist:
            # extract the 1st integer in each item
            found_int = re.search("\d+", item)
            list_int.append(found_int.group())

        pipe_int = ""
        for items in list_int:
            pipe_int = pipe_int + items + ","
        # remove the last symbol ","
        pipe_int = pipe_int[:-1]

        # produce the condition string
        condstr = field_name + " IN ("+ pipe_int+")"


    #
    # (5) format the output string
    #
    if Need_Check == "no":
        format_string = Template_No_Constraint.replace('name', field_name)
        format_string = format_string.replace('type', FType)
        format_string = format_string.replace('null_str', null_str)

    if Need_Check == "yes":
        format_string = Template_Constraint.replace('fieldname', field_name)
        format_string = format_string.replace('type', FType)
        format_string = format_string.replace('null_str', null_str)

        format_string = format_string.replace('tablename', target_table.upper())
        # replace the conditions
        format_string = format_string.replace('conditions', condstr)

    return format_string

def main():

    # check the arguments
    # print 'Number of arguments:', len(sys.argv), 'arguments.'
    print "program name : ", sys.argv[0]
    print "csv file : ", sys.argv[1]
    print "Start program."

    if len(sys.argv) == 1:
        print "Please specify the csv file."
        sys.exit()

    if len(sys.argv) > 2:
        print "Too many. Read one csv file at at time."
        sys.exit()

    filename = sys.argv[1]
    #print filename

    # read csv file
    file = csv.reader(open(filename, "rb"));

    # open text file to write
    o_fname = filename + ".sql"
    o_file = open(o_fname, "w")

    # look at the second column, find the right table to work on
    # You can specify which table to work on !!!
    for row in file:
        tablename = row[1]
        tablename = tablename.strip()
        if tablename == target_table:

            row_temp = GenTemplate(row)

            # output the row_temp to the text file
            o_file.write(row_temp)

    # close output file
    o_file.close()

    #
    print "End program.\n",\
        "The decimal case is not considered here.\n",\
        "You still need to manually fix the output."

    return 0



if __name__ == '__main__':
    main()


