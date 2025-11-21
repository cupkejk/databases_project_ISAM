from main import tests, single_sorting, file_contents

print("Do you want to:\n1. Run the tests + graph\n2. perform a single sorting")
option = input()
while int(option) != 1 and int(option) != 2:
    print("INCORRECT OPTION! CHOOSE AGAIN:")
    option = input()

option = int(option)

if option == 1:
    tests()
else:
    single_sorting()