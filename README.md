Challenger is a script for zetaboards. It was designed to host film challenges.

##Install

- Rename config.ini.txt to config.ini
- Fill all the missing values in config.ini
- If you want to monitor more than one thread create another section
in config.ini called [thread1], [thread2], etc. with forumid and threadid 
variables under each section.
- Create a template for each section in template/ directory
- Run main.py

##Usage

The program will scan every page in a given thread. For each post it will 
attempt to find lines that begin with the following patterns:

5. Citizen Kane<br>
6-7. City Lights, The Gold Rush<br>
8.-9. Rear Window, Vertigo

If a user makes a mistake they may post a new comment that includes 
!overwrite N, where N is the number of seen films. It is also possible
to include the command when there's a need to overwrite 
e.g. a large numbered list that would mess up the statistics.
