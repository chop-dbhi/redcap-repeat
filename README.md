RedCap&trade; preprocess script
=================

Preprocess script for RedCap&trade; data dictionaries witten by CBMi to support custom types and repeating fields.

RedCap&trade; is a great tool. It allows anyone to quickly and easily create and share case report forms and surveys. But sometimes to capture common concepts, or multiple instances of a single concept, you need to create groups of fields with complex branching logic over and over. This preprocess script seeks to solve this problem.

## Specify commonly used field types in one line
Instead of manually creating multiple RedCap&trade; fields to capture data for a single discrete value, use a custom type, and let this preprocess script do all the hard work. Let's see a few examples.

### Minimum and Maximum

Instead of creating two RedCap&trade; number fields to capture a range of numbers, just use the minmax field type. Give the preprocess script this:

Field Name |  Field Type |  Field Label            |Text Validation Type |
-----------|-------------|-------------------------|---------------------|
temp       | minmax      | Temperature $placeholder| number              |

and it will turn it into this:

Field Name  |  Field Type |  Field Label            |  Text Validation Type |
------------|-------------|-------------------------|-----------------------|
temp\_minimum| text        |   Temperature minimum  | number                |
temp\_maximum| text        |   Temperature maximum  | number                |

All other columns will be preserved just as you would expect. 

### Checkbox with Other

Specify checkbox\_other to automatically create a checkbox field followed by a text field to specify further details. The branching logic to only show the details field when the Other choice is selected will be written for you.


Field Name |  Field Type         |  Field Label            | Choices                               |
-----------|---------------------|-------------------------|---------------------------------------|
relative   | checkbox\_other      | Affected relatives      | 1, Mom &#124;  2, Dad &#124; 3, Other | 

will become:


Field Name     |  Field Type         |  Field Label            | Choices                               |Branching Logic|
---------------|---------------------|-------------------------|---------------------------------------|---------------|
relative       | checkbox            | Affected relatives      | 1, Mom &#124;  2, Dad &#124; 3, Other |  		   |
relative\_other | text                | Other Affected relatives|                                      |[relative(3)] = '1'|

#### Controlling the language used in the Field Label for generated fields
The preprocess script tries to use very generic language for generated Field Labels. Placing a pipe in the Field Label field followed by something like this

	Please specify $placeholder relative
	
will allow you to control the generated Field Label, producing this

	Please specify other relative
	
A specific example:

	
Field Name |  Field Type         |  Field Label            | Choices                               |
-----------|---------------------|-------------------------|---------------------------------------|
temp       | checkbox\_other      | Affected relatives &#124; Please specify $placeholder affected relative| 1, Mom &#124;  2, Dad &#124; 3, Other |

will become:

Field Name |  Field Type         |  Field Label            | Choices                               |Branching Logic|
-----------|---------------------|-------------------------|---------------------------------------|---------------|
temp       | checkbox            | Affected relatives      | 1, Mom &#124;  2, Dad &#124; 3, Other |			   |
temp\_other | text               | Please specify other affected relative|                          |[temp(3)] = '1'|

### Checkbox with details for each option

Similar to checkbox\_other, the checkbox\_details type will create textbox fields that will show for each checkbox selected. It works the same way as the checkbox\_other except for creating additionally conditional fields.

### Radio/Dropdown other and Radio/Dropdown with details

There are equivalent custom types for radio and dropdown (radio\_other, radio\_details, dropdown\_other, and dropdown\_details) that work exactly the same as the checkbox\_other and checkbox\_details types.

### Age in weeks and days
The custom type age\_weeks\_days will create the two individual week and day fields with the correct range restrictions. This is especially useful for capturing gestational age.

For example:

Field Name      |  Field Type    |  Field Label                 | Min Value | Max Value|
----------------|----------------|------------------------------|-----------|----------|
gestational\_age | age\_weeks\_days | Gestational age $placeholder |           |          |

becomes:

Field Name            |  Field Type    |  Field Label                 | Min Value | Max Value|
----------------------|----------------|------------------------------|-----------|----------|
gestational\_age\_weeks | text           | Gestational age in weeks     | 0         |   52     |
gestational\_age\_days  | text           | Gestational age in days      | 0         |   6      |

### Age in years and months

There is a custom field available for age in years and months as well. Specify the type as age\_years\_months to use it. It works exactly the same as age\_weeks\_days

### Value with Units

For a measurement and value that requires units to be specified, use the value\_with\_units custom type.

Field Name            |  Field Type      |  Field Label                 |
----------------------|------------------|------------------------------|
potassium\_level       | value\_with\_units | Potassium level              |

becomes:

Field Name                  |  Field Type      |  Field Label                 | Text Validation Type
----------------------------|------------------|------------------------------|---------------------
potassium\_level            | text             | Potassium level              | number
potassium\_level\_units     | text             | Potassium level units        | 

#### Convenience unit types
There are two convenience unit types that work the same way as value\_with\_unit, but instead of a free text input for units, provide a dropdown with specific choices. These are

* weight\_value\_with\_units
* height\_value\_with\_units

## Repeating fields

RedCap&trade; does not support the ability to specify that a given field repeats a variable number of times. For example, specifyng a list of medications requires creating a number of medicine fields and various complex branching schemes. The preprocess script can help.

### The Basics

To specify that a field repeats, use the following in the field name column:

\<field\_name\> repeat \<maximum number of times field repeats\> \<Name of Repeat\>

The \<Name of Repeat\> attribute will be used to construct a question asking the user how many times the field repeats. For example

Field Name                              |  Field Type      |  Field Label                 | Branching Logic
----------------------------------------|------------------|------------------------------|-----------------
medication repeat 3 Patient Medication  | text             | Patient medication           |

will become:

Field Name  |  Field Type      |  Field Label                                          | Text Validation Type | Text Validation Min        | Text Validation Max| Branching Logic
------------|------------------|-------------------------------------------------------|----------------------|----------------------------|--------------------|----------------
medication\_group\_no | text     | How many patient medications would you like to enter? |      number          | 0                          |   3                |
medication1         | text     | Patient medication 1                                  |                      |                            |                    | [medication\_group\_no] >= 1
medication2         | text     | Patient medication 2                                  |                      |                            |                    | [medication\_group\_no] >= 2
medication3         | text     | Patient medication 3                                  |                      |                            |                    | [medication\_group\_no] >= 3

### Controlling the Field Label

By default, when creating the field label for a repeated field, the preprocess script looks for the \<Name of Repeat\> in the Field Label and puts a number after it. If that behavior is not what you want, you can control where the number goes by putting $d in the field label. Use $s if you would like the number to be of the style 1st, 2nd, 10th, etc. For example

Field Name                              |  Field Type      |  Field Label                 | Branching Logic
----------------------------------------|------------------|------------------------------|-----------------
medication repeat 3 Patient Medication  | text             | $s patient medication        |  

will become:

Field Name  |  Field Type      |  Field Label                                          | Text Validation Type | Text Validation Min        | Text Validation Max| Branching Logic
------------|------------------|-------------------------------------------------------|----------------------|----------------------------|--------------------|----------------
medication\_group\_no | text     | How many patient medications would you like to enter? |      number          | 0                          |   3                |
medication1         | text     | 1st patient medication                                |                      |                            |                    | [medication\_group\_no] >= 1
medication2         | text     | 2nd patient medication                                |                      |                            |                    | [medication\_group\_no] >= 2
medication3         | text     | 3rd Patient medication                                |                      |                            |                    | [medication\_group\_no] >= 3

### Controlling the Field Name

By default, the generated Field Names for repeated groups just place a number at the end. If you would like the number to go elsewhere, put ${d} anywhere in the Field Label.

For example:

Field Name                 |  Field Type      |  Field Label                 | Branching Logic
---------------------------|------------------|------------------------------|------------------
gene${d}\_name repeat 4 Gene | text           | Gene $d name                |

will become:

Field Name    |  Field Type |  Field Label                         | Text Validation Type | Text Validation Min        | Text Validation Max| Branching Logic
--------------|-------------|--------------------------------------|----------------------|----------------------------|--------------------|----------------
gene\_group\_no | text        | How many genes do you want to enter? |      number          | 0                          |   4                |
gene1\_name    | text        | Gene 1 name                          |                      |                            |                    | [gene\_group\_no] >= 1
gene2\_name    | text        | Gene 2 name                          |                      |                            |                    | [gene\_group\_no] >= 2
gene3\_name    | text        | Gene 3 name                          |                      |                            |                    | [gene\_group\_no] >= 3
gene4\_name    | text        | Gene 4 name                          |                      |                            |                    | [gene\_group\_no] >= 4


### Repeating groups of fields

Sometimes you want a group of fields to repeat instead of just a single field. For example, you might be trying to capture date and result of a series of hand xrays. To do this, follow the same rules for single field repeats except change "repeat" to "startrepeat" and terminate the repeating group by putting "endrepeat" after the Field Label of the last field in the group.
For example:

Field Name                      |  Field Type      |  Field Label        | Choices                | Text Validation Type | Branching Logic
--------------------------------|------------------|---------------------|------------------------|----------------------|----------------
xray\_date startrepeat 3 xray    | text             | $s xray data        |                        |   date               |
xray\_hand                       | radio            | $s xray hand        | 1, Right &#124; 2, Left|                      |
xray\_result endrepeat           | notes            | Result of $s xray   |                        |                      |

will become:

Field Name    |  Field Type |  Field Label                         | Choices                | Text Validation Type | Text Validation Min        | Text Validation Max| Branching Logic
--------------|-------------|--------------------------------------|------------------------|----------------------|----------------------------|--------------------|----------------
xray\_group\_no | text        | How many xrays do you want to enter? |                        |      number          | 0                          |   3                |
xray\_date1    | text        | 1st xray date                        |                        |      date            |                            |                    | [xray\_group\_no] >= 1
xray\_hand1    | radio       | 1st xray hand                        |1, Right &#124; 2, Left |                      |                            |                    | [xray\_group\_no] >= 1
xray\_result1  | notes       | Result of 1st xray                   |                        |                      |                            |                    | [xray\_group\_no] >= 1
xray\_date2    | text        | 2nd xray date                        |                        |      date            |                            |                    | [xray\_group\_no] >= 2
xray\_hand2    | radio       | 2nd xray hand                        |1, Right &#124; 2, Left |                      |                            |                    | [xray\_group\_no] >= 2
xray\_result2  | notes       | Result of 2nd xray                   |                        |                      |                            |                    | [xray\_group\_no] >= 2
xray\_date3    | text        | 3rd xray date                        |                        |      date            |                            |                    | [xray\_group\_no] >= 3
xray\_hand3    | radio       | 3rd xray hand                        |1, Right &#124; 2, Left |                      |                            |                    | [xray\_group\_no] >= 3
xray\_result3  | notes       | Result of 3rd xray                   |                        |                      |                            |                    | [xray\_group\_no] >= 3


### Nesting groups of repeating fields

Sometimes a single group of repeating fields may not be enough. For example, you might be trying to capture a list of medications, each with a list of side affects. To accomplish this you can nest startrepeat-endrepeat groups or single repeat fields inside of other startrepeat-endrepeat groups. The behavior should be just as you would expect. The only additional functionality is that you can use $s1 or $d1 in Field Labels to refer to the iteration of outer groups. For example, $s will always refer to the current (innermost) group, and $1 will always refer to the outermost group. If you had 2 nested groups, $1 would refer to the iteration of the outermost group, $2 would refer to the iteration of the middle group, and $s would still refer to the iteration of the innermost group. Examples should clear this up.

Field Name                                         |  Field Type      |  Field Label        | Text Validation Type | Branching Logic
---------------------------------------------------|------------------|---------------------|----------------------|-----------------------|----------------
medication${d}\_name startrepeat 3 Medication       | text             | $s medication name               |                       |
sideaffect repeat 3 Side Affect                    | text             | $s side affect of medication $d1 |                       |
medication${d}\_date endrepeat                      | text             | Date $s medication taken         | date                  |

will become:

Field Name                      |  Field Type |  Field Label                                | Text Validation Type  | Text Validation Min | Text Validation Max| Branching Logic
--------------------------------|-------------|---------------------------------------------|-----------------------|---------------------|--------------------|---------------------------------------------|
med\_group\_no             | text        | How many medications do you want to enter? |  number                | 0                 |   3                |                                      |
med1\_name                | text        | 1st medication name                        |                        |                       |                 | [med\_group\_no] >= 1               | 
med1\_sideaffect\_group\_no | text        | How many side affects do you want to enter? |  number             | 0                     |   3             | [med\_group\_no] >= 1             |
med1\_sideaffect1         | text        | 1st side affect for medication 1           |                        |                       |                 | [med1\_sideaffect\_group\_no] >= 1  |
med1\_sideaffect2         | text        | 2nd side affect for medication 1           |                        |                       |                 | [med1\_sideaffect\_group\_no] >= 2  |
med1\_sideaffect3         | text        | 3rd side affect for medication 1           |                        |                       |                 | [med1\_sideaffect\_group\_no] >= 3  |
med1\_date                | text        | Date 1st medication taken                  |  date                  |                       |                 | [med\_group\_no] >= 1               |
med2\_name                | text        | 2nd medication name                        |                        |                       |                 | [med\_group\_no] >= 2               |
med2\_sideaffect\_group\_no | text        | How many side affects do you want to enter?|  number                | 0                     |   3           | [med\_group\_no] >= 2             |
med2\_sideaffect1         | text        | 1st side affect for medication 2           |                        |                       |                 | [med2\_sideaffect\_group\_no] >= 1  |
med2\_sideaffect2         | text        | 2nd side affect for medication 2           |                        |                       |                 | [med2\_sideaffect\_group\_no] >= 2  |
med2\_sideaffect3         | text        | 3rd side affect for medication 2           |                        |                       |                 | [med2\_sideaffect\_group\_no] >= 3  |
med2\_date                | text        | Date 2nd medication taken                  | date                   |                       |                 | [med\_group\_no] >= 2               |
med3\_name                | text        | 3rd medication name                        |                        |                       |                 | [med\_group\_no] >= 3               |
med3\_sideaffect\_group\_no | text        | How many side affects do you want to enter?|  number                | 0                     |   3           | [med\_group\_no] >= 3             |
med3\_sideaffect1         | text        | 1st side affect for medication 3           |                        |                       |                 | [med3\_sideaffect\_group\_no] >= 1  |
med3\_sideaffect2         | text        | 2nd side affect for medication 3           |                        |                       |                 | [med3\_sideaffect\_group\_no] >= 2  |
med3\_sideaffect3         | text        | 3rd side affect for medication 3           |                        |                       |                 | [med3\_sideaffect\_group\_no] >= 3  |
med3\_date                | text        | Date 3rd medication taken                  |     date               |                       |                 | [med\_group\_no] >= 3               |

If a nested repeating group or field is actually the last field of its parent group then add a blank row with the following as Field Name (note the leading space):
    
" endrepeat"


For example, in the above example, if you wanted the side affects to be the last thing entered for each medication (rather than the date), it would have to look like this:

Field Name                                         |  Field Type      |  Field Label        | Text Validation Type | Branching Logic
---------------------------------------------------|------------------|---------------------|----------------------|-----------------------|----------------
medication${d}\_name startrepeat 3 Medication       | text             | $s medication name               |                       |
medication${d}\_date                                | text             | Date $s medication taken        | date                  |
sideaffect repeat 3 Side Affect                    | text             | $s side affect of medication $d1 |                       |
&nbsp;endrepeat                                    |                  |                                  |                       |

### Repeating field prompt modes
By default, the preprocess script will generate a question before each repeating item asking how many you would like to enter and then show that many instances of the field. There are two other modes controlled by flags on the command prompt. Using -a will cause the preprocess script to automatically show the first instance of the repeating item, and as the first field in each repeating group of fields is filled in, it will show the next repeating field. Using the -p flag will cause the preprocess script to add a checkbox field after each repeating group asking if you would like to enter another.

## Branching logic details

The preprocess script will try to preserve any branching logic you put in place ahead of time while inserting any necessary additional logic. The intention is that it should work as one would expect. If a situation is encountered where this is not true, please report it.

## Custom fields within repeating fields/groups
Custom field types should work seamlessly with repeating fields and should not require any additional work. If any bugs are encountered, please report them.

## Caveats
 
This is beta software. It has been used internally for one complex project but there are sure to be unexpected edge cases. Please make sure to backup any data dictionary files you run through the preprocess script. This has not been test on calculated fields used within repeating groups.


## Usage
The preprocess script is written in python. It has no required external dependencies, but you may want to install the python inflector package which will help properly pluralize repeating item names in generated questions. To install the inflector, issue the following from the command prompt:
	
	easy_install inflector
	
To execute the preprocess script, call it from the command prompt as follows:

	python redcap_preprocess.py "name of input file" "name of output file"
	
Use the -h flag to see a description of available options.

