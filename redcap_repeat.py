#!/bin/python
#Copyright (c) 2012, The Children's Hospital of Philadelphia All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
#following conditions are met:
#
#1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#   disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#   following disclaimer in the documentation and/or other materials provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
#INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
#USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import os
import csv
import re
import sys
import copy
import json
import logging
# New comment
from optparse import OptionParser
from collections import defaultdict
from string import Template
from functools import partial
try:
    import inflector
    pluralize = inflector.English().pluralize
except:
    pluralize = lambda x : "%ss" % x

# Users can specify a file that maps group names to their correct pluralization
plurals = {}
if os.path.isfile("plurals.json"):
    plurals_file = open("plurals.json")
    try:
        plurals = json.load(plurals_file)
    except:
        pass
    finally:
        plurals_file.close()

logger = logging.getLogger("redcap_preproces")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

begin  =  re.compile(r'([a-zA-Z_0-9${}]+)? +(repeat|startrepeat) +([][a-z_0-9]*) +(\w.*)')
end  = re.compile(r'([a-zA-Z_0-9${}]+)? +(endrepeat) *')

other_id_re = re.compile(r'\[([a-z_0-9]*)\]')
other_id_with_num_re = re.compile(r'\[([a-z_0-9]*)\](\d+)')

paren_re = re.compile(r'([a-zA-Z0-9 ]*)(\([a-zA-Z0-9 ]*\))')

key = {'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7,'i':8,'j':9,'k':10,'l':11,'m':12, 'p':15}
number_map = {0:"th", 1:"st", 2:"nd", 3:"rd", 4:"th", 5:"th", 6:"th", 7:"th", 8:"th", 9:"th"}

template = []
for x in range(0,15):
    template.append("")

def numberEnding(iteration):
    if iteration % 100 > 10 and iteration % 100 < 20:
        return "th"
    else:
        return number_map[iteration % 10]

def extract(cell, regex):
     match = regex.match(cell)
     if match:
         groups = match.groups()
         return {
            "match":True,
            "id": groups[0], 
            "meta":groups[1:], 
         }
     else:
         return { "match": False }

extract_begin = partial(extract, regex=begin)
extract_end = partial(extract, regex=end)

def clean(x):
    return x.replace(" ","_").replace("/","_").replace("(","_").replace(")","_").lower()

def preserve_metadata(position, extension, cell):
    meta = None 
    meta1 = extract_begin(cell)
    meta2 = extract_end(cell)
    if meta1['match']:
        meta = meta1
    if meta2['match']:
        meta = meta2
    
    if not meta or not meta['match'] or position not in {'begin':1, 'end':1}:
        return "%s%s" % (cell.split(" ")[0], extension)
    
    new_cell = cell
    if meta['match'] and meta['meta'][0] == "repeat":
        # if it was a minimum field marked as repeat, we need to map it to a startrepeat end repeat
        if position == "begin":
            new_cell =  "%s%s %s" % (meta["id"], extension, "startrepeat %s %s" % meta['meta'][1:])
        else:
            new_cell = "%s%s %s" % (meta["id"], extension, "endrepeat")
    elif meta['match'] and meta['meta'][0] == "startrepeat":
        if position == "begin":
            new_cell = "%s%s %s" % (meta["id"], extension, "startrepeat %s %s" % meta['meta'][1:])
        else:
            new_cell = "%s%s" % (meta["id"], extension)
    elif meta['match'] and meta['meta'][0] == "endrepeat":
        if position == "begin":
            new_cell= "%s%s" % (meta["id"], extension)
        else:
            new_cell = "%s%s %s" % (meta["id"], extension, "endrepeat")


    return new_cell

def minmax(line, minimum="minimum", maximum="maximum"):
    min_line = line[:]
    max_line = line[:]
    
    # Don't copy section headers
    max_line[key['c']] = ""

    min_line[key['a']] = preserve_metadata("begin", "_" + clean(minimum),  min_line[key['a']])
    max_line[key['a']] = preserve_metadata("end", "_"+clean(maximum), max_line[key['a']])

    min_line[key['d']] = "text"
    max_line[key['d']] = "text"

    min_line[key['e']] = Template(min_line[key['e']]).safe_substitute(placeholder=minimum)
    max_line[key['e']] = Template(max_line[key['e']]).safe_substitute(placeholder=maximum)
    return [min_line, max_line]

def details(line, kind = "checkbox", detail_kind = "text", details = None ):
    choices = line[key['f']].split("|")
    choices = [x.split(",") for x in choices]
    try:
        choices = [(x[0].strip(), x[1].strip()) for x in choices]
    except IndexError:
        sys.stderr.write("Error processing record %s, please check that the field choices all have a comma"
            " between the number and the choice.\n" % line[key['a']])
        sys.exit()

    if details == None:
        details = [x[1].lower() for x in choices]

    description = line[key['e']].split(" | ")
    new_line = line[:]
    new_line[key['a']] = preserve_metadata("begin", "", line[key['a']])
    new_line[key['e']] = description[0]
    new_line[key['d']] = kind

    new_lines = [new_line]

    last_detail = None
    for index, choice in choices:
       if choice.lower() in details:
           # if its an other field default to a better wording
           if len(details) == 1 and details[0] == "other":
               prompt = "Please specify other %s" % description[0]
           else:
               prompt = "Please specify details for %s" % choice
           if len(description) > 1:
                 prompt = Template(description[1]).safe_substitute(placeholder = choice)
           other_line = line[:]
           other_line[key['a']] = preserve_metadata("middle", "_%s_dtls" % clean(choice), line[key['a']])
           other_line[key['d']] = detail_kind
           other_line[key['f']] = ""
           other_line[key['e']] = prompt
           if kind == "checkbox":
               other_line[key['l']] = "[%s(%s)]='1'" % (line[key['a']].split(" ")[0], index)
           else:
               other_line[key['l']] = "[%s]='%s'" % (line[key['a']].split(" ")[0], index)
           last_detail = choice
           # Don't repeat section headings
           other_line[key['c']] = ""
           new_lines.append(other_line)
    if last_detail == None:
        sys.stderr.write("Error: For record '%s', since the datatype is of type '*_other' you must specify an 'other'"
                " choice, chosen from one of the following values: %s \n" % (line[key['a']], details))
        sys.exit()
    # Go back and fix the last one
    new_lines[-1][key['a']] = preserve_metadata("end", "_%s_dtls" % clean(last_detail), line[key['a']])

    return new_lines

def checkbox_mutex_other (line, kind = "checkbox", detail_kind = "descriptive", details = None, other = False):
    #create a list of choices by splitting all the options at the "|" character
    choices = line[key['f']].split("|")
    choices = [x.split(",") for x in choices]
    size = len(choices)
    #convert all the choices to lower case and then create a list with all the options selected by the user
    details = [x[1].lower() for x in choices]
    description = line[key['e']].split(" | ")
    new_line = line[:]
    new_line[key['a']] = preserve_metadata("begin", "", line[key['a']])
    new_line[key['e']] = description[0]
    new_line[key['d']] = kind

    new_lines = [new_line]
    
    for index, choice in choices:
        x = choice.lower()
        x = x.lstrip('  ')
        x = x.rstrip('  ')
        index = index.lstrip(' ')
        #create list of all possible none/unknown options
        mutexes = ['none', 'unknown', 'result not known', 'unknown/not documented', 'unknown or not reported']
        #check for the existence of each one in the list of choices
        for mutex in mutexes:
            if x == mutex:
                prompt = "You selected %s and another answer choice. Please revise your answer." % mutex
                other_line = line[:]
                other_line[key['a']] = preserve_metadata("middle", "_%s" % clean(x), line[key['a']])
                other_line[key['d']] = detail_kind
                other_line[key['f']] = ""
                other_line[key['e']] = prompt
                #deal with the instance if there is only two options
                if size <= 2 and index == 1:
                    other_line[key['l']] = "[%s(%s)]='1' and [%s(%s)] = '1'" % (line[key['a']].split(" ")[0], index, line[key['a']].split(" ")[0], int(index) + 1)
                elif size <= 2 and index == 2:
                    other_line[key['l']] = "[%s(%s)]='1' and [%s(%s)] = '1'" % (line[key['a']].split(" ")[0], index, line[key['a']].split(" ")[0], int(index) - 1)
                #more than two options
                else:
                    for z in range(3, size + 1):
                        branching_string = "[%s(%s)]='1' and ([%s(%s)] = '1' or "
                        string_add = "[%s(%s)] = '1' or "
                        string_final = "[%s(%s)] = '1')"
                        branching_final = branching_string+(size-3)*string_add+string_final
                        sub_list = (line[key['a']].split(" ")[0], index)
                        for r in range(1,int(index)):
                            sub_list = sub_list + (line[key['a']].split(" ")[0], r)
                        for r in range(int(index) + 1, size + 1):
                            sub_list = sub_list + (line[key['a']].split(" ")[0], r)
                        other_line[key['l']] = branching_final % sub_list
                new_lines.append(other_line)
        if x == 'other' and other == True:
            other_line = line[:]
            other_line[key['a']] = preserve_metadata("middle", "_%s" % clean(x), line[key['a']])
            other_line[key['d']] = "notes"
            other_line[key['f']] = ""
            prompt = "Please specify details for %s" % x
            other_line[key['e']] = prompt
            other_line[key['l']] = "[%s(%s)]='1'" % (line[key['a']].split(" ")[0], index)
            new_lines.append(other_line)
    new_lines[-1][key['a']] = preserve_metadata("end", "_%s" % clean(x), line[key['a']])
    return new_lines

def value_units(line, kind = "dropdown", units = [], just_units = False):
    units_line = line[:]
    value_line = line[:]
    weight = False
    if "kg" in units:
        weight = True
    # If this is used to weight units and the user enters lb, we also need to collect ounces
    oz_line = line[:]

    value_line[key['c']] = ''

    units_line[key['a']] = preserve_metadata("begin", "_units",  units_line[key['a']])
    if not weight:
        value_line[key['a']] = preserve_metadata("end", "", value_line[key['a']])
    else:
        value_line[key['a']] = preserve_metadata("middle", "", value_line[key['a']])
        oz_line[key['a']] =  preserve_metadata("end", "_oz", value_line[key['a']])

    units_line[key['d']] = kind
    value_line[key['d']] = "text"
    oz_line[key['d']] = "text"

    units_line[key['h']] = ""
    oz_line[key['h']] = ""

    value_line[key['e']] = Template(value_line[key['e']]).safe_substitute(placeholder="").strip()
    units_line[key['e']] = Template(units_line[key['e']]).safe_substitute(placeholder="").strip()
    oz_line[key['e']] = Template(oz_line[key['e']]).safe_substitute(placeholder="").strip()

    units_line[key['e']] = "%s units" % units_line[key['e']]
    oz_line[key['e']] = "%s ounces" % oz_line[key['e']]

    if weight:
        if len(value_line[key['g']].strip()):
            value_line[key['g']] = "%s (%s)" % (value_line[key['g']], "If units are lbs, specify ounces below")
        else:
            value_line[key['g']] = "If units are lbs, specify ounces below"

    # Only show oz when lbs are the units
    oz_line[key['l']] = "[%s] = '1'" % units_line[key['a']]
    oz_line[key['g']] = ""

    if len(units):
       units_line[key['f']] = " | ".join(["%d, %s" % x for x in enumerate(units)])

    units_line[key['g']] = ""
    
    if just_units:
       return [units_line]
    
    return [units_line, value_line] if not weight else [units_line, value_line, oz_line]

def age_weeks_days(line):
    weeks_line = line[:]
    days_line = line[:]

    days_line[key['c']] = ""

    weeks_line[key['d']] = "text"
    days_line[key['d']] = "text"
    
    weeks_line[key['h']] = "integer"
    days_line[key['h']] = "integer"

    weeks_line[key['i']] = 0
    weeks_line[key['j']] = 52

    days_line[key['i']] = 0
    days_line[key['j']] = 6

    weeks_line[key['e']] = "%s in full weeks" % weeks_line[key['e']]
    days_line[key['e']] = "%s in days (partial week)" % days_line[key['e']]

    weeks_line[key['a']] = preserve_metadata("begin", "_weeks",  weeks_line[key['a']])
    days_line[key['a']] = preserve_metadata("end", "_days", days_line[key['a']])

    weeks_line[key['g']] = "Specify partial week in days below"
    days_line[key['g']] = ""

    return [weeks_line, days_line]

def age_years_months(line):
    years_line = line[:]
    months_line = line[:]
    
    months_line[key['c']] = ""

    years_line[key['d']] = "text"
    months_line[key['d']] = "text"
    
    years_line[key['h']] = "integer"
    months_line[key['h']] = "integer"

    years_line[key['i']] = 0
    years_line[key['j']] = 100 

    months_line[key['i']] = 0
    months_line[key['j']] = 11

    years_line[key['e']] = "%s in full years" % years_line[key['e']]
    months_line[key['e']] = "%s additional months (partial year)" % months_line[key['e']]

    years_line[key['a']] = preserve_metadata("begin", "_years",  years_line[key['a']])
    months_line[key['a']] = preserve_metadata("end", "_months", months_line[key['a']])

    years_line[key['g']] = "Specify partial years in months below"
    months_line[key['g']] = ""

    return [years_line, months_line]

def value_with_units_and_minmax(line, units_kind = "dropdown",  minimum="minimum", maximum="maximum", just_units=False):
    new_lines = value_units(line, kind = units_kind, just_units = just_units)
    line[key['c']] = ""
    new_lines.extend(minmax(line, minimum=minimum, maximum=maximum))
    length = len(new_lines)
    for index, line in enumerate(new_lines):
        if index == 0:
            line[key['a']]= preserve_metadata("begin", "", line[key['a']])
        elif index != length - 1:
            line[key['a']]= preserve_metadata("middle", "", line[key['a']])
        else:
            line[key['a']]= preserve_metadata("end", "", line[key['a']])
    return new_lines



dispatch = defaultdict(lambda : lambda x: [x])
dispatch['minmax'] = minmax
dispatch['value_with_weight_units'] = partial(value_units, units=["kg","lb"])
dispatch['value_with_length_units'] = partial(value_units, units=["in","cm"])
dispatch['value_with_units'] = partial(value_units, kind = "text")
dispatch['value_with_units_and_minmax'] = partial(value_with_units_and_minmax, units_kind = "text")
dispatch['value_with_units_and_normal_range'] = partial(value_with_units_and_minmax, units_kind = "text", minimum = "normal range minimum", maximum="normal range maximum")
dispatch['range_with_units'] = partial(value_with_units_and_minmax, units_kind = 'text', just_units = True)

dispatch['age_weeks_days'] = age_weeks_days
dispatch['age_years_months'] = age_years_months 

dispatch['checkbox_other'] = partial(details, details = ["other"])
dispatch['checkbox_details'] = details
dispatch['checkbox_details_text'] = details
dispatch['checkbox_details_note'] = partial(details, detail_kind = "note")
dispatch['checkbox_other_text'] = partial(details, details = ["other"])
dispatch['checkbox_other_note'] = partial(details, details = ["other"], detail_kind = "note")

dispatch['radio_other'] = partial(details, kind = "radio", details = ["other"])
dispatch['radio_details'] = partial(details, kind = "radio")
dispatch['radio_details_text'] = partial(details, kind = "radio")
dispatch['radio_details_note'] = partial(details, kind = "radio", detail_kind = "note")
dispatch['radio_other_text'] = partial(details, kind = "radio", details = ["other"])
dispatch['radio_other_note'] = partial(details, kind = "radio", details = ["other"], detail_kind = "note")

dispatch['dropdown_other'] = partial(details, kind = "dropdown", details = ["other"])
dispatch['dropdown_details'] = partial(details, kind = "dropdown")
dispatch['dropdown_details_text'] = partial(details, kind = "dropdown")
dispatch['dropdown_details_note'] = partial(details, kind = "dropdown", detail_kind = "note")
dispatch['dropdown_other_text'] = partial(details, kind = "dropdown", details = ["other"])
dispatch['dropdown_other_note'] = partial(details, kind = "dropdown", details = ["other"], detail_kind = "note")

#adding dispatch for the checkbox_mutex_other function
dispatch['checkbox_mutex'] = checkbox_mutex_other
dispatch['checkbox_mutex_other'] = partial(checkbox_mutex_other, other = True)

def repeat_group(group, path=[], ids={}, depth=0, iterations=[], parent_group=[], branch="", pre_logic=""):
    depth += 1
    first = group[0]
    last = group[-1]

    if first != last:
    # Last could be a single row that just matched " endrepeat", if so, throw it out
        match = end.match(last[key['a']])
        if match and match.group(0) == " endrepeat":
            group = group[:-1]
            last = group[-1]
    new_rows = []
    show_instance = None
    match = begin.match(first[key['a']])
    # This parameter can be a few things
    # 1) A number, which indicates this is a variably repeating group
    # 2) [Another ID] which indicates this group will repeat a number of times based on the value of another entry
    #    This will search for this value and try to use its upper bound value for the maximum number of fields
    #    If it cannot find it, it will use the default from the options object, which is 10
    # 3) [Another ID]10 which indicates the same as above, but with a specified maximum
    try:
        times = int(match.group(3))
    except ValueError:
        other_id_match = other_id_re.match(match.group(3))
        other_id_max_match = other_id_with_num_re.match(match.group(3))
        if other_id_match:
            for line in parent_group:
                if line[key['a']].split(" ")[0] == other_id_match.group(1):
                    if line[key['j']].isdigit():
                        times = int(line[key['j']])
                    break
            else:
                times = options.max_repeat
            show_instance = other_id_match.group(1)
        elif other_id_max_match:
            times = int(other_id_max_match.group(2))
            show_instance = other_id_max_match.group(1)
        else:
            logger.error("Error on following line: %s" % first)
            sys.exit()

    name = match.group(4)
    prefix = "_".join(path)
    if len(prefix):
        prefix = prefix + "_"
    clean_name = clean(name)
    name_pattern = re.compile(re.escape(name), re.IGNORECASE)
    another_branch = branch
    
    # If in the default mode, which asks prompts the user up front for the number of items in each repeating group, add that question here
    # If show_instance is already defined, then it means this group repeats a number determined by a previous question's value
    if not (options.auto or options.prompt) and not show_instance:
        number_line = template[:]
        number_line[key['a']] = show_instance = "%s%s_%s" % (prefix, re.sub(' ','_', clean_name ), "group_no")
        number_line[key['b']] = first[key['b']]
        number_line[key['d']] = "text"
        if not options.groups:
            plural_name = name
            plural_match = paren_re.match(plural_name)
            
            if plurals.has_key(name.lower()):
                 plural_name = plurals[name.lower()]
            elif plural_match:
                plural_name = plural_match.group(1).strip()
                plural_name = plural_name.lower() if not plural_name.isupper() else plural_name
                plural_name = pluralize(plural_name)
                plural_name = plural_name + " " + plural_match.group(2)
            else:
                 plural_name = plural_name.lower() if not plural_name.isupper() else plural_name
                 plural_name = pluralize(plural_name)
            
            number_line[key['e']] = "How many %s would you like to enter (up to %d)?" % (plural_name, times)
            number_line[key['c']] = Template(first[key['c']]).safe_substitute(placeholder = plural_name)
        else:
            number_line[key['e']] = "How many %s %s would you like to enter (up to %d)?" % (name.lower() if not name.isupper() else name, options.groups, times)
            number_line[key['c']] = Template(first[key['c']]).safe_substitute(placeholder = "%s %s" % (name.lower() if not name.isupper() else name, options.groups))


        if not options.validation_off:
            number_line[key['h']] = "integer"
            number_line[key['i']] = "0"
            number_line[key['j']] = times
        logic = first[key['l']]
        if len(logic.strip()):
           for pairs in ids.items():
                id_pair = pairs[1]
                logic = re.sub(id_pair[0],id_pair[1],logic)
        if len(pre_logic) and len(logic.strip()):
            logic = "(%s) and [%s]>=%d"%(logic, pre_logic, iterations[depth-2])
        elif len(pre_logic):
            logic = "[%s]>=%d"%(pre_logic, iterations[depth-2])


        pre_logic = number_line[key['a']]
        
        number_line[key['l']] = logic
        new_rows.append(number_line)

    for iteration in range(1, times+1):
        skip = 0
        # We need to find all the possible keys that might need replacing this time around
        group_ids = [line[key['a']].split(" ")[0] for line in group]
        ids.update(dict([("\[%s(?=(]|\())" % re.escape(cell),(re.compile("\[%s(?=(]|\())"% re.escape(cell)), Template("["+prefix+cell).safe_substitute(d=iteration) if "${d}" in cell else "[%s%s%d" % (prefix, cell, iteration))) for cell in group_ids]))
        for index, line in enumerate(group):
             if skip:
                 skip = skip - 1 
                 continue

             # Section headers
             if not (options.auto or options.prompt) and not show_instance and index == 0 and iteration == 1:
                 if not options.groups: #TODO REFACTOR
                     plural_name = name
                     plural_match = paren_re.match(plural_name)

                     if plurals.has_key(name.lower()):
                          plural_name = plurals[name.lower()]
                     elif plural_match:
                         plural_name = plural_match.group(1).strip()
                         plural_name = plural_name.lower() if not plural_name.isupper() else plural_name
                         plural_name = pluralize(plural_name)
                         plural_name = plural_name + " " + plural_match.group(2)
                     else:
                          plural_name = plural_name.lower() if not plural_name.isupper() else plural_name
                          plural_name = pluralize(plural_name)
                     line[key['c']] = Template(line[key['c']]).safe_substitute(placeholder = plural_name)
                 else:
                     line[key['c']] = Template(line[key['c']]).safe_substitute(placeholder = "%s %s" % (name.lower() if not name.isupper() else name, options.groups))
             else:
                line[key['c']] = ""

             startmatch = begin.match(line[key['a']])
             if index >= 1 and startmatch:
                 # found a nested group
                 new_path = path[:]
                 new_path.append("%s%d" % (clean_name, iteration))
                 nested_group = find_group(group[index:])
                 logger.debug("Found nested Group %s - length %d" % (line[key['a']], len(nested_group)))
                 logger.debug("Last member is %s" % nested_group[-1][key['a']])
                 iterations.append(iteration)
                 new_rows.extend(repeat_group(nested_group, new_path, copy.copy(ids), depth, iterations, group, another_branch, pre_logic))
                 iterations.pop()
                 # The number of lines in the nested group represents lines we don't process
                 # as part of this group
                 #if nested_group[-1][key['a']] == " endrepeat":
                 #    skip = len(nested_group)
                 #else:
                 skip = len(nested_group)-1
                 continue
             # business as usual
             new_line = line[:]
             first_cell =  line[key['a']].split(" ")[0]
             new_line[key['a']] = prefix + (Template(first_cell).safe_substitute(d=iteration) if "${d}" in first_cell else "%s%d" % (first_cell, iteration))
             
             # Take care of the prompt for this line
             # It can do the following things:
             # If percent %d or %s is found, it will insert the number (1) , or the stringized version of the number there (1st, 2nd)
             # if $group# is found, it will sub in the appropriate group number in each spot
             # Failing all else, it will try to find the name in the prompt and add a number after it
             prompt = line[key['e']]
             
             template_map = {}
             for d in range(0, depth-1):
                 template_map["d"+str(d+1)]=iterations[d] 
                 template_map["s"+str(d+1)]=str(iterations[d])+numberEnding(iterations[d])
             template_map['d'] = iteration
             template_map['s'] = str(iteration)+numberEnding(iteration)
             new_line[key['e']] = Template(prompt).safe_substitute(**template_map)
             #If everything failed, try to replace the group name with group name #
             
             if new_line[key['e']] == line[key['e']]:
                if name_pattern.search(prompt):
                   new_line[key['e']] = prompt = name_pattern.sub("%s %d" % (name, iteration), prompt)
             # Determine the Branching Logic
             logic = line[key['l']]

             # Subsitute in proper var names
             if len(logic.strip()):
                for pairs in ids.items():
                     id_pair = pairs[1]
                     logic = re.sub(id_pair[0],id_pair[1],logic)
             # Use the correct scheme for generating the next visible one
             if (options.auto or options.prompt) and not show_instance: 
                 if another_branch:
                     if len(logic.strip()):
                        new_line[key['l']] = "(%s) and %s" % (logic, another_branch)
                     else:
                        new_line[key['l']] = another_branch
                 else:
                     new_line[key['l']] = logic
             else:
                 if len(logic.strip()):
                     new_line[key['l']] = "(%s) and %s" % (logic, "[%s]>=%d" % (show_instance, iteration))
                 else:
                     new_line[key['l']] = "[%s]>=%d" % (show_instance, iteration)

             # Support for matrix group name
             if (len(new_line) - 1) >= key['p']:
                 if new_line[key['p']].strip():
                     new_line[key['p']] = "%s%s%d" % (prefix, new_line[key['p']],iteration) 

             if options.validation_off:
                new_line[key['h']] = new_line[key['i']] = new_line[key['j']] = ''

             new_rows.append(new_line)
        # If using prompt or auto scheme, generate the logic to use for the next group 
        # If show_instance is defined but one of these is also true, it means this
        # group repeats a number of times dependent on the answer to another question
        if options.prompt and iteration < times and not show_instance:
            another_line = new_line[:]
            another_line[key['a']] = "%s%s_repeat%s" % (prefix, clean_name, iteration)
            another_line[key['d']] = "checkbox"
            another_line[key['e']] = ""
            another_line[key['f']] = "1, Add another %s?" % name
            another_branch = "[%s(1)]='1'" % ("%s%s_repeat%s" % (prefix, clean_name, iteration))
            if iteration == 1:
                another_line[key['l']] = new_rows[0][key['l']]
            else:
                another_line[key['l']] = "[%s(1)]='1'" % ("%s%s_repeat%s" % (prefix, clean_name, iteration-1))
            new_rows.append(another_line)
        elif options.auto and iteration < times and not show_instance:
            # There is a slight complication here because checkboxes can't easily be tested for being null
            first_prev = group[0]
            if first_prev[key['d']] == "checkbox":
                group_cell = first_prev[key['a']].split(" ")[0]
                choices = first_prev[key['f']].split(" | ")
                choices = [x.split(",")[0].strip() for x in choices]
                cell_name = Template(prefix+group_cell).safe_substitute(d = iteration) if "${d}" in group_cell else "%s%s%d" % (prefix, group_cell, iteration)
                another_branch = "("
                for choice in choices:
                    if len(another_branch) > 1:
                        operator = " or "
                    else:
                        operator = ""
                    another_branch = another_branch + operator + "[%s(%s)] = '1'" % (cell_name, choice)
                another_branch = another_branch + ")"
            else:
                group_cell = first_prev[key['a']].split(" ")[0]
                another_branch = '[%s] <> ""' % (Template(prefix+group_cell).safe_substitute(d = iteration) if "${d}" in group_cell else "%s%s%d" % (prefix, group_cell, iteration))

    return new_rows


def find_group(lines):
    group = []
    depth = 0
    for line in lines:
        startmatch = begin.match(line[key['a']])
        endmatch = end.match(line[key['a']])
        group.append(line)
        if startmatch:
            depth += 1
        if endmatch or (startmatch and startmatch.group(2)=="repeat"):
            depth -= 1
        if depth == 0:
            return group


def main(input_file, output_file):

    temp_file = os.tmpfile() 

    handle_in = open(input_file, 'rU')
    handle_out = open(output_file, 'wb')

    input_f = csv.reader(handle_in)
    output_f = csv.writer(temp_file)

    # this is the preprocessor 
    for line in input_f:
        for generated_line in dispatch[line[key['d']]](line):
            output_f.writerow(generated_line)

    temp_file.seek(0)
    handle_in.close()
    
    input_f = csv.reader(temp_file)
    output_f = csv.writer(handle_out)

    # now handle repeating groups
    outer_group=[]
    group = []
    depth = 0
    for line in input_f:
        startmatch = begin.match(line[key['a']])
        endmatch = end.match(line[key['a']])

        if startmatch:
            depth += 1
        if depth:
            group.append(line)
        else:
            output_f.writerow(line)
            outer_group.append(line)
        if endmatch or (startmatch and startmatch.group(2)=="repeat"):
            depth -= 1

        if depth == 0 and len(group):
            logger.debug("Found group %s, length - %d" % (group[0][key['a']], len(group)))
            for row in repeat_group(group, parent_group = outer_group):
                output_f.writerow(row)
            group = []

    handle_out.close()
    temp_file.close()


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-p", "--prompt_to_add", default=False, dest="prompt", action="store_true",
            help="Instead of inserting a question upfront asking for the number of instances, ask to add another after each group.")
    parser.add_option("-a", "--auto_add", default=False, dest="auto", action="store_true", 
            help="Instead of inserting a question upfront asking the number of instances, automatically display a new group as soon as the first item"
            "of the previous group is entered.")
    parser.add_option("-g", "--group_name", dest="groups", default=False, action="store",
            help="The name you would like to use for groups in generated questions. For example, if set to 'items', a generated questions would be: 'How many medication"
            "items would you like to enter?' By default, if this is not specified repeat group name would be pluralized, and the sentence would be 'How many medications would you like to enter?'")
    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help = "Print debug statements. Useful for determine what groups and nested groups have been found.")
    parser.add_option("-m", "--max_repeat", default=10, dest="max_repeat", action="store",
            help="The maximum number of repeating groups to use in situations where it is not defined.")
    parser.add_option("-v", "--validation_off", default=False, dest="validation_off", action="store_true",
            help="Disable use of REDCap input validation")
    (options, args) = parser.parse_args()

    if options.auto and options.prompt:
        print "--prompt_add and --auto_add are mutually exclusive. Please choose one. See --help for more details."
        sys.exit()
    if options.debug:
        logger.setLevel(logging.DEBUG)

    main(args[0], args[1])
