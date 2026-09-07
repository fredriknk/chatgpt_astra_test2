# KICAD TEMPLATE 

This is the kicad template i use for my projects. The latest addition is a build_outputs.py automating picture generation, 3d models and sch/prints, Gerbers ETC! Pretty sweet!

SO! What you have to do is use kicad9+ with kikit installed through the kicad terminal and make a new project inside ./CAD, copy the two lib package3d folders into the project, then open "generate_outputs.(bat/sh)" depending if youre on windows/linux and edit the line
 
set "PROJECT=.\CAD\\<proj_name>\\<proj_name>"
or
PROJECT_DEFAULT="CAD/<proj_name>/<proj_name>"

to your project name. Then you can delete this readme, and it will set up a new readme with linked pictures and files based on the Readme.template.md when you run the script. Every time you run it after (if the README.md exists) it will just update the output files.



