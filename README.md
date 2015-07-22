Challenger is a script for zetaboards. It was designed to host film challenges.

##Install

- Rename config.ini.txt to config.ini
- Fill all the missing values in config.ini
- If you want to monitor more than one thread create another section
in config.ini called [thread1], [thread2], etc. with forumid and threadid 
variables under each section.
- Create a template for each section in template/ directory (e.g. thread0.html)
- Create a template for announcing winners for each section in template/ directory (e.g. thread0-winners.html)
- Run main.py
- To add or remove threads simply add or remove them in config.ini (works on-the-fly)

##Usage

The program will scan every (new) page in a given thread. For each (new) 
post it will attempt to find lines that begin with the following patterns:

```
5. Citizen Kane
6-7. City Lights, The Gold Rush
8.-9. Rear Window, Vertigo
```

The program selects the highest number it can find and assigns that 
number to the username. When all (new) posts have been scanned the program
will render a template file and updates the first post with the results.

If a user makes a mistake they may post a new comment that includes 
!overwrite N, where N is the number of seen films. It is also possible
to include the command when there's a need to overwrite 
e.g. a large numbered list that would mess up the statistics.
