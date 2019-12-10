#! /usr/bin/python

# Standard Library Modules
import time  # allows using time.

# Third-Party Modules
import pandas  # allows data formatting.
import netmiko  # allows SSH connections.


class bcolors:  # Defining a class for built-in colors.
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def connection_function():
    """ SSH Connection to the MDS using the Netmiko Module """

    # Defining the net_connect variable which will represent the session with the MDS.
    net_connect = None

    try:  # Attempting a connection using the netmiko module with its "ConnectHandler" class to the specified MDS.
        net_connect = netmiko.ConnectHandler(device_type = "cisco_nxos",
                                            ip = raw_input("Enter the MDS IP: "),
                                            username = raw_input("Enter your RADIUS username: "),
                                            password = raw_input("Enter your RADIUS password: "))
        print ("------------------------------------------------------------------------------------")
        # Printing out the MDS name that we are connecting to by using the "base_prompt" attribute.
        print bcolors.BOLD + ("!!! Connecting to  {} !!!\n".format(net_connect.base_prompt)) + bcolors.ENDC

    except:
        raise Exception(bcolors.FAIL + "Failed to connect to the specified MDS" + bcolors.ENDC)

    # Returning the session that has been created to allow reusage of the same session for all commands.
    return net_connect


def send_command(command, connection):
    """ Sending a command to the MDS using the Netmiko SSH Connection """

    try:  # Sending a command to the MDS session using the "send_command" class.
        command_output = connection.send_command(command)
        return command_output

    except:  # Catching a command failure exception.
        print bcolors.FAIL + "This command MAY have failed - {}".format(command) + bcolors.ENDC


def get_port_info_function(connection):
    """ Gets all of the info needed for the functions in the script,
    returns three port lists - single-flogi/multi-flogi/storage ports """

    # All of the initiator's FLOGI port list
    init_ports = send_command('show flogi database | '
                                  'exc "\|'
                                  'it will be wwn" | cut -d " " -f 1', connection)

    # All of the target's FLOGI port list
    target_ports = send_command('show flogi database | ' it will be wwn
                                  'grep "
" | cut -d " " -f 1', connection)

    # Two lists (one - initiator, two - target)...
    # containing all Initiator & Target Port records (each record is an element in the list)
    init_portlist = init_ports.split("\n")[3:-3]
    target_portlist = target_ports.split("\n")

    # Removes empty list elements
    init_portlist = filter(lambda interface: interface != "", init_portlist)
    final_target_portlist = filter(lambda interface: interface != "", target_portlist)

    # Create lists to determine single-flogi interfaces & multi-flogi interfaces
    final_multiflogi_portlist = []  # Empty final multi-flogi port list
    final_singleflogi_portlist = []  # Empty final single-flogi port list

    # Run a loop on initiator interfaces and filter to two lists - single & multi flogi.
    for interface in init_portlist:
        # If the interface is already in the single-flogi list then he must have multiple FLOGI
        if interface in final_singleflogi_portlist:
            final_singleflogi_portlist.remove(interface)
            final_multiflogi_portlist.append(interface)

        # If the interface is not in the single FLOGI list and not in the multi-flogi list, then it is single FLOGI.
        elif interface not in final_singleflogi_portlist and interface not in final_multiflogi_portlist:
            final_singleflogi_portlist.append(interface)

    return  (final_singleflogi_portlist, final_multiflogi_portlist, final_target_portlist)


def find_alias(flogi_list, connection):
    """ Find a Device Alias of a specified PWWN """

    # The device alias database,
    device_alias_database = send_command('show device-alias database', connection)

    # For each element in the given FLOGI list (single/multi/target etc.)...
    for pwwn in flogi_list:
        # If the PWWN is in the Device Alias database
        if pwwn[1] in device_alias_database:
            continue
        # If the PWWN is NOT in the Device Alias database
        else:
            pwwn.append("No Alias")

    # Create a new list where each element is a record (in string format) from the Device Alias database.
    device_alias_database = device_alias_database.split("\n")

    # Modify the list using list comprehension by turning each element into a list on its own.
    device_alias_database = [element.split() for element in device_alias_database]

    # For each record (list) in the device alias database...
    for record in device_alias_database:
        # For each FLOGI record in the given FLOGI list...
        for pwwn in flogi_list:
            # If the PWWN is inside the Device Alias Database record...
            if pwwn[1] in record:
                pwwn.append(record[2])

    return flogi_list


def find_zone(flogi_list, connection):
    """ Find Zones for each PWWN in a given list """

    # Full Zone Database on a specified MDS.
    zone_database = send_command('show zone', connection)

    # Create a list for PWWNs without a Zone
    no_zone = []

    # For each FLOGI record in a given FLOGI list...
    for pwwn in flogi_list:
        # If the PWWN is in the Zone Database...
        if pwwn[1] in zone_database:
            continue
        # If the PWWN is NOT in the Zone Database...
        else:
            # Append "No Zones" to each element in the FLOGI list, and add the FLOGI record to the "no_zone" list.
            pwwn.append("No Zones")
            no_zone.append(pwwn)

    # For each FLOGI record in the FLOGI database.
    for pwwn in flogi_list:
        # If the FLOGI record is not part of the "No Zone" list --> HAS a Zone Name...
        if pwwn not in no_zone:
            # Filter out only the specific Zone Name and append to the FLOGI record list element.
            zone_name = send_command('show zone member pwwn {} | grep zone | cut -d " " -f 4'
                                    .format(pwwn[1]), connection)
            pwwn.append(zone_name)

    return flogi_list


def single_flogi_ports(port_list, connection):
    """ Finds records for ports with only one FLOGI, meaning Rack servers/IBM blades """

    # FLOGI records of initiator ports.
    initiator_flogi = send_command('show flogi database | '
                                  'exc 
it will be wwn
                                  '"', connection)

    # List of all Port records with a single FLOGI (each record is an element in the list).
    initiator_flogi_list = initiator_flogi.split("\n")[3:-3]

    # Runs a nested loop on all of the initiator flogi records and all of the ports that have a single flogi.
    # Appends FLOGI records of only single-flogi interfaces,
    # and then removes the FLOGI record with said interface to avoid duplicates.
    single_flogi_list = []
    for flogi in initiator_flogi_list:
        for interface in port_list:
            if interface in flogi:
                single_flogi_list.append(flogi)
                port_list.remove(interface)

    # List Comprehension - Splits each FLOGI record by spaces, thus creating a list for each element.
    single_flogi_list = [element.split() for element in single_flogi_list]

    # List Comprehension - Takes each third list element for each element in the main (single-flogi) list.
    # The list will contain the interface and its PWWN.
    single_flogi_list = [element[::3] for element in single_flogi_list]

    # Return the single FLOGI list where each element is a list in and of itself that contains the interface and WWPN.
    return single_flogi_list


def multiple_flogi_ports(flogi_list, connection):
    """ Finds ports with multiple FLOGI, meaning HP Blades/Cisco Blades """

    # All of the initiator's FLOGI database.
    init_flogi = send_command('show flogi database | '
                                  'exc 
                                  ' it will be wwn "', connection)

    # List of all Initiator FLOGI records (each record is an element in the list).
    init_flogi_list = init_flogi.split("\n")[3:-3]  # The element numbers are to avoid irrelevant lines in the output.

    # Removes empty list elements from the initiator port list.
    init_flogi_list = filter(lambda interface: interface != "", init_flogi_list)

    # Create an empty list which will contain each FLOGI record as an element.
    multi_flogi_list = []

    # "For" loop on the initiator flogi list and a "for" loop on each port with multi-flogi...
    for flogi in init_flogi_list:
        for interface in flogi_list:
            # Append FLOGI records of multi-flogi ports to the "multi_flogi_list" list.
            if interface in flogi:
                multi_flogi_list.append(flogi.split())

    # Create an empty list - the final multi flogi list...
    # that will contain each element as a list by its own where element 0 == port number, and element 1 == PWWN ;
    final_multi_flogi_list = []

    # For each FLOGI record in the "multi_flogi_list"...
    for flogi in multi_flogi_list:
        # Append elements with a step of 3, meaning the element 0 (port number) and element 3 (PWWN)
        final_multi_flogi_list.append(flogi[::3])

    return final_multi_flogi_list


def storage_ports(flogi_list, connection):
    """ Find ports that go to a Storage Machine (Targets) """

    # All of the storage ports, found by grep'ing their PWWNs...
    target_list = send_command('show flogi database | grep "
\|' it will be wwn
                "', connection)

    '''
    List of all Target FLOGI records (each record is an element in the list).
    [3:-3] The element numbers were used to avoid irrelevant lines in the output,
    but proved to be unreliable for all kinds of output, therefore removed.
    '''
    target_flogi_list = target_list.split("\n")

    # Removes empty list elements from the target port list.
    target_flogi_list = filter(lambda interface: interface != "", target_flogi_list)

    # Create an empty list which will contain each FLOGI record as an element.
    storage_flogi_list = []

    # "For" loop on the target flogi list and a "for" loop on each port with multi-flogi...
    for flogi in target_flogi_list:
        for interface in flogi_list:
            # Append FLOGI records of target ports to the "multi_flogi_list" list.
            if interface in flogi:
                storage_flogi_list.append(flogi.split())

    # Create an empty list where each element will be a list containing a port number with its PWWN.
    final_storage_flogi_list = []

    # For each FLOGI record in the "storage_flogi_list"...
    for flogi in storage_flogi_list:
        # Append elements with a step of 3, meaning the element 0 (port number) and element 3 (PWWN)
        final_storage_flogi_list.append(flogi[::3])

    return final_storage_flogi_list


def excel(single_flogi_list, multi_flogi_list, target_flogi_list):
    """ Input: three lists - single-flogi/multi-flogi/target and a file path for the excel workbook,
        Output: Organized Excel Workbook in the specified file path """

    file_path = raw_input("Enter the file path: ")  # A string containing the file path for the excel workbook.

    # Creating three sets of four lists (overall - 12 lists) with single-flogi/multi-flogi/target information
    single_interface_list = []
    single_pwwn_list = []
    single_alias_list = []
    single_zone_list = []

    multi_interface_list = []
    multi_pwwn_list = []
    multi_alias_list = []
    multi_zone_list = []

    target_interface_list = []
    target_pwwn_list = []
    target_alias_list = []
    target_zone_list = []

    # Create three "for" loops that run on the three specified function lists...
    # Append interfaces, PWWNs, Device Alias', and Zones into four different lists.
    for flogi in single_flogi_list:
        single_interface_list.append(flogi[0])
        single_pwwn_list.append(flogi[1])
        single_alias_list.append(flogi[2])
        single_zone_list.append(flogi[3])

    for flogi in multi_flogi_list:
        multi_interface_list.append(flogi[0])
        multi_pwwn_list.append(flogi[1])
        multi_alias_list.append(flogi[2])
        multi_zone_list.append(flogi[3])

    for flogi in target_flogi_list:
        target_interface_list.append(flogi[0])
        target_pwwn_list.append(flogi[1])
        target_alias_list.append(flogi[2])
        target_zone_list.append(flogi[3])

    # Create three "Pandas" dataframes (single-flogi/multi-flogi/targets) using elements from the lists generated above.
    single_sheet = pandas.DataFrame({'Interface (Port)': single_interface_list,
                                     'Device Alias (Server Name)': single_alias_list,
                                     'PWWN (Port World Wide Name)': single_pwwn_list,
                                     'Zone(s)': single_zone_list})

    multi_sheet = pandas.DataFrame({'Interface (Port)': multi_interface_list,
                                    'Device Alias (Server Name)': multi_alias_list,
                                    'PWWN (Port World Wide Name)': multi_pwwn_list,
                                    'Zone(s)': multi_zone_list})

    target_sheet = pandas.DataFrame({'Interface (Port)': target_interface_list,
                                     'Alias': target_alias_list,
                                     'PWWN (Port World Wide Name)': target_pwwn_list,
                                     'Zone(s)': target_zone_list})

    # Create an Excel Workbook with "Pandas" using "XlsxWriter" as the engine.
    writer = pandas.ExcelWriter(file_path, engine='xlsxwriter')

    # Convert the "pandas" dataframes to "XlsxWriter" Excel objects.
    single_sheet.to_excel(writer, sheet_name = 'IBM Blades|All Rack Servers')
    multi_sheet.to_excel(writer, sheet_name = 'HP|Cisco Blades')
    target_sheet.to_excel(writer, sheet_name = 'Targets (Storage Ports)')

    # Get the XlsxWriter workbook and worksheet objects.
    workbook = writer.book
    worksheet = writer.sheets['HP|Cisco Blades']
    worksheet = writer.sheets['IBM Blades|All Rack Servers']
    worksheet = writer.sheets['Targets (Storage Ports)']

    #Close the Pandas Excel writer and output the Excel file.
    writer.save()


def main():
    """ Main Function """

    # Variables
    start = time.time()  # Saving a point-in-time to determine the start time of the program.
    connection = connection_function()  # Assigning the connection function to the connection variable.

    if connection:  # If the connection succeeded (== True)...

        # Initial sequence for gathering all of the port information.
        get_port_info = get_port_info_function(connection)
        if get_port_info:  # If the "get_port_info" function succeeded (== True)...
            final_singleflogi_portlist = get_port_info[0]  # The first element that is returned by the function.
            final_multiflogi_portlist = get_port_info[1]  # The second element that is returned by the function.
            final_target_portlist = get_port_info[2]  # The third element that is returned by the function.

            # Print the three lists
            print "Here are the three lists returned by the function 'get_port_info': "
            print final_singleflogi_portlist
            print final_multiflogi_portlist
            print final_target_portlist

            # Single FLOGI sequence ---> code for ports with single FLOGI records.
            single_flogi_list = single_flogi_ports(final_singleflogi_portlist, connection)  # Find PWWN for each port.
            if single_flogi_list:
                new_single_flogi_list = find_alias(single_flogi_list, connection)  # Find Device Alias for each PWWN.

                if new_single_flogi_list:
                    global single_with_zone  # Move list to global scope --> visible to anything under main() function.
                    single_with_zone = find_zone(new_single_flogi_list, connection)  # Find zone for each PWWN.
                    print "Single FLOGI final list: ", single_with_zone  # Print the list.

            # Multi FLOGI sequence ---> code for ports with multiple FLOGI records.
            multi_flogi_list = multiple_flogi_ports(final_multiflogi_portlist, connection)  # Find PWWN for each port.
            if multi_flogi_list:
                new_multi_flogi_list = find_alias(multi_flogi_list, connection)  # Find Device Alias for each PWWN.

                if new_multi_flogi_list:
                    global multi_with_zone  # Move list to global scope --> visible to anything under main() function.
                    multi_with_zone = find_zone(new_multi_flogi_list, connection)  # Find zone for each PWWN.
                    print "Multi FLOGI final list: ", multi_with_zone  # Print the list.


            # Target FLOGI sequence ---> code for storage ports (targets).
            target_flogi_list = storage_ports(final_target_portlist, connection)
            if target_flogi_list:
                new_target_flogi_list = find_alias(target_flogi_list, connection)

                if new_target_flogi_list:
                    global target_with_zone
                    target_with_zone = find_zone(new_target_flogi_list, connection)
                    print "Target FLOGI final list: ", target_with_zone  # Print the list.

            # Create an excel workbook with all of the above information from the three sequences.
            workbook = excel(single_with_zone, multi_with_zone, target_with_zone)

            # Print final statement
            print "The script has finished running, check the file path you specified for viewing the Excel workbook"

        else:
            raise Exception("The 'get_port_info' function has failed")

    else:  # In case the connection to the MDS has failed...
        raise Exception("The connection to the MDS has failed (connection() function)")

    end = time.time()  # Saving a point-in-time to determine the end time of the program.
    print "The program runtime is {} seconds".format(end - start)  # Printing the runtime of the program in seconds.

if __name__ == '__main__':
    main()
