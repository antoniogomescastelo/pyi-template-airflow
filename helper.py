import sys
from collibra_luigi_client.helper import Helper

if __name__ == '__main__':
    print(Helper(argv=sys.argv[1:]).get_configuration_password())
