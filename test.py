import sys, os

## print(sys.argv[1])
 
# Displaying the script path
print(__file__)
 
# Displaying the parent directory of the script
print(os.path.dirname(os.path.abspath(__file__)))