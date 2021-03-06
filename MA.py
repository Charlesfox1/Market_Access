# -*- coding: utf-8 -*-

## library Imports
import pandas as pd
import numpy as np
import json, os, time
try:
        import urllib.request as url   # python 3
except:
        import urllib2 as url  # python 2

import sys, getopt
import shapely

#### SET DEFAULT VARIABLES ####
# these can be overidden by using the tag commands brought up if you use -h
# when running the script
infile = r'merged_df.csv'
infile_2 = r'not_found!'
lat_name = 'Lat'
lon_name = 'Long'
limit = 0
call_type = 'OSRM'
UID = 'Unique_ID'
Pop = 'vNTL_PopD_GPW_2015'
ffpath = r'C:\Users\charl\Documents\Market Access\curl'
rescue = 0
rescue_num = 0
MB_Toke = r'[insert your mapbox token here]'

helpstr = """\nCommands recognised for this script:\n
        \n\t-p   Path - string for input and output folder path
        \n\t-f   File name of .csv containing input data
        \n\t-m   Latitude column name.
        \n\t-n   Longitude column name
        \n\t-o   Origin Unique Identifier column name (e.g. District, Name, Object ID...).
             This is mainly helpful for joining the output back to the input data / a shapefile,
             and is non-essential in terms of the calculation. It can be text or a number.
        \n\t-q   Population / weighting column name
        \n\t-c   Server call type - "OSRM" for OSRM, "MB" for Mapbox, "MBT" for Mapbox with traffic, or "Euclid" for Euclidean distances (as the crow flies)

        \n\t*** Optional - if sources =/= destinations. Note - Unique identifier and Pop column names must remain the same ***
        \n\t-l   Limit - use this to limit the coordinate input list (int). Optional.
        \n\t-D   Filename of destinations csv
        \n\t-R   Save - input latest save number to pick up from there
        \n\t-Z   Rescue number parameter - if you have already re-started the process, denote how many times. First run = 0, restarted once = 1...
        \n\nDo NOT put column names or indeed any input inside quotation marks.
        \nThe only exceptions is if the file paths have spaces in them.
        \n"""

# Import variables
try:
        opts, args = getopt.getopt(sys.argv[1:],"hp:f:m:n:o:q:c:l:D:R:Z:",['ffpath','infile','latitude','longitude','UID','Pop','call_type','limit','infile_dest', 'rescue','resnum'])
except getopt.GetoptError:
        print('**Check inputs by typing -h. This program will now exit**')
        sys.exit(2)
limit, rescue, rescue_num = 0, 0, 0 # assign dummy vars; limit + resuce does not apply unless specified in call
for opt, arg in opts:
        if opt == '-h':
                print(helpstr)
                sys.exit()
        elif opt in ("-p", "--ffpath"):
                ffpath = arg
        elif opt in ("-f", "--infile"):
                infile = arg
        elif opt in ("-m", "--latitude"):
                lat_name = arg
        elif opt in ("-n", "--longitude"):
                lon_name = arg
        elif opt in ("-o", "--UID"):
                UID = arg
        elif opt in ("-q", "--Pop"):
                Pop = arg
        elif opt in ("-c", "--call_type"):
                call_type = arg
        elif opt in ("-l", "--limit"):
                limit = arg
                limit = int(limit)
        elif opt in ("-D", "--infile_dest"):
                infile_2 = arg
        elif opt in ("-R", "--rescue"):
                rescue = arg
                rescue = int(rescue)
        elif opt in ("-Z", "--resnum"):
                rescue_num = arg
                rescue_num = int(rescue_num)
#print(opts)
start = time.time()
print('\nChosen server: %s\n\nStart time: %s' % (call_type, time.ctime(start)))
print('Origins: %s' % infile)
print('Destinations: %s\n' % infile_2)

# Save settings
save_rate = 5
def save(returns, j, i, numcalls, rescue_num):
        elapsed_mins = (time.time() - start)/60
        elapsed_secs = (time.time() - start)%60
        total = ((numcalls / float(i)) * (time.time() - start)/60.0)
        remaining = total - elapsed_mins
        print ('\n______________________________________\n')
        print ('\nSave point %s. Running for: %d minutes %d seconds' % (j, elapsed_mins, elapsed_secs))
        print ('\ncalls completed: %d of %d. Est. run time: %d minutes. Time remaining: %d' % (i-1, numcalls, total, remaining))
        print ('\npercentage complete: %d percent' % (((i-1) / float(numcalls)*100)))
        print ('\n______________________________________\n')
        try:
                df = pd.concat(returns)
        except:
                df = returns
        df.to_csv(os.path.join(ffpath,'temp_file_%d.csv' % rescue_num))

def save_current(O_list, D_list):
        O_df = pd.DataFrame({'Origins': O_list})
        S_df = pd.DataFrame({'Destinations': D_list})
        curr = pd.concat([O_df,S_df], ignore_index=True, axis=1)
        curr.columns = ['Origin', 'Desintation']
        curr.to_csv(os.path.join(ffpath, 'Current_O_D_combo.csv'))

# File Import for sources file
input_df = pd.read_csv(os.path.join(ffpath, infile))
input_df['source_list'] = input_df[lon_name].map(str).str.cat(input_df[lat_name].map(str), sep = ',')
input_df['source_list'] = input_df['source_list']+';'
source_list = input_df['source_list'].values.tolist()
source_UIDs = input_df[UID].values.tolist()
#input_df['source_point'] = input_df.apply(lambda x: Point(x[lon_name],x[lat_name]), axis = 1)
#source_points = input_df['source_point'].tolist()

# Look to import separate file for destinations; if not, set destinations = sources
try:
        input_df2 = pd.read_csv(os.path.join(ffpath, infile_2))
        input_df2['dest_list'] =  input_df2[lon_name].map(str).str.cat(input_df2[lat_name].map(str), sep = ',')
        input_df2['dest_list'] = input_df2['dest_list']+';'
        dest_list = input_df2['dest_list'].values.tolist()
        dest_UIDs = input_df2[UID].values.tolist()
        #input_df2['dest_points'] = input_df2.apply(lambda x: Point(x[lon_name],x[lat_name]), axis = 1)
        #dest_points = input_df2['dest_points'].tolist()
except:
        dest_list = source_list
        dest_UIDs = source_UIDs
        #dest_points = source_points
        pass

# apply limit if in test mode
if limit > 0:
        source_list = source_list[:limit]
        dest_list = dest_list[:limit]
        source_UIDs = source_UIDs[:limit]
        dest_UIDs = dest_UIDs[:limit]
        #dest_points = dest_points[:limit]
        #source_points = source_points[:limit]

# Function for calling Mapbox server.
def MapboxCall(O_list, D_list, i, O_IDs, D_IDs):

        # prevent server annoyance
        print('Call to Mapbox server number: %d' % i)

        # Mapbox - construct request
        header = 'https://api.mapbox.com/directions-matrix/v1/mapbox/driving/'

        # Convert origins to HTTP request string
        Os = ';'.join(str(coord).replace("'", "").replace(";", "") for coord in O_list)

        # Destinations to HTTP request string
        Ds = ';'.join(str(coord).replace("'", "").replace(";", "") for coord in D_list)

        # Join them together
        data = Os+';'+Ds

        # Add mapbox token key here
        token = MB_Toke

        # Define which coords in data string are origins, and which are destinations
        sources = ['%d' % x for x in range(0,len(O_list))]
        sources = ';'.join(str(x).replace("'", "") for x in sources)
        lenth = len(O_list)+len(D_list)
        destinations = ['%d' % x for x in range(len(O_list),lenth)]
        destinations = ';'.join(str(x).replace("'", "") for x in destinations)

        # Build request string
        request = header+data+'?sources='+sources+'&destinations='+destinations+'&access_token='+token

        # Pass request to interweb
        r = url.urlopen(request)

        # Error handle
        try:
                # Convert Bytes response to readable Json
                MB_TelTest_json = json.loads(r.read().decode('utf-8'))
                data_block = MB_TelTest_json['durations']
        except:
                data_block = 'null'
        # Build df from JSON
        #sources_label = [str(i['location']) for i in MB_TelTest_json['sources']]
        #dest_label = [str(i['location']) for i in MB_TelTest_json['destinations']]
        sources_label = O_IDs
        dest_label = D_IDs
        chunk = pd.DataFrame(data = data_block,
                                  columns = dest_label,
                                  index = sources_label)
        # Convert to minutes, stack 2D array to 1D array
        chunk = chunk.stack(level =-1)
        chunk.columns = ['O','D','DIST']
        return chunk

# Function for calling Mapbox Traffic server.
def MapboxCallTraffic(O_list, D_list, i, O_IDs, D_IDs):

        # prevent server annoyance
        print('Call to Mapbox Traffic server number: %d' % i)

        # Mapbox - construct request
        header = 'https://api.mapbox.com/directions-matrix/v1/mapbox/driving-traffic/'

        # Convert origins to HTTP request string
        Os = ';'.join(str(coord).replace("'", "").replace(";", "") for coord in O_list)

        # Destinations to HTTP request string
        Ds = ';'.join(str(coord).replace("'", "").replace(";", "") for coord in D_list)

        # Join them together
        data = Os+';'+Ds

        # Add mapbox token key here
        token = MB_Toke

        # Define which coords in data string are origins, and which are destinations
        sources = ['%d' % x for x in range(0,len(O_list))]
        sources = ';'.join(str(x).replace("'", "") for x in sources)
        lenth = len(O_list)+len(D_list)
        destinations = ['%d' % x for x in range(len(O_list),lenth)]
        destinations = ';'.join(str(x).replace("'", "") for x in destinations)

        # Build request string
        request = header+data+'?sources='+sources+'&destinations='+destinations+'&access_token='+token

        # Pass request to interweb
        r = url.urlopen(request)

        # Error handle
        try:
                # Convert Bytes response to readable Json
                MB_TelTest_json = json.loads(r.read().decode('utf-8'))
                data_block = MB_TelTest_json['durations']
        except:
                data_block = 'null'
        # Build df from JSON
        #sources_label = [str(i['location']) for i in MB_TelTest_json['sources']]
        #dest_label = [str(i['location']) for i in MB_TelTest_json['destinations']]
        sources_label = O_IDs
        dest_label = D_IDs
        chunk = pd.DataFrame(data = data_block,
                                  columns = dest_label,
                                  index = sources_label)
        # Convert to minutes, stack 2D array to 1D array
        chunk = chunk.stack(level =-1)
        chunk.columns = ['O','D','DIST']
        return chunk

# Function for calling OSRM server.
def OSRMCall(O_list, D_list, i, O_IDs, D_IDs):

        # prevent server annoyance
        print('Call to OSRM server number: %d' % i)

        # Mapbox - construct request
        header = 'http://router.project-osrm.org/table/v1/driving/'

        # Convert origins to HTTP request string
        Os = ';'.join(str(coord).replace("'", "").replace(";", "") for coord in O_list)

        # Destinations to HTTP request string
        Ds = ';'.join(str(coord).replace("'", "").replace(";", "") for coord in D_list)

        # Join them together
        data = Os+';'+Ds

        # Define which coords in data string are origins, and which are destinations
        sources = ['%d' % x for x in range(0,len(O_list))]
        sources = ';'.join(str(x).replace("'", "") for x in sources)
        lenth = len(O_list)+len(D_list)
        destinations = ['%d' % x for x in range(len(O_list),lenth)]
        destinations = ';'.join(str(x).replace("'", "") for x in destinations)

        # Build request string
        request = header+data+'?sources='+sources+'&destinations='+destinations

        # Pass request to interweb
        r = url.urlopen(request)

        # Error handle
        try:
                # Convert Bytes response to readable Json
                MB_TelTest_json = json.loads(r.read().decode('utf-8'))
                data_block = MB_TelTest_json['durations']
        except:
                data_block = 'null'

        # Build df from JSON
        #sources_label = [str(i['location']) for i in MB_TelTest_json['sources']]
        #dest_label = [str(i['location']) for i in MB_TelTest_json['destinations']]
        sources_label = O_IDs
        dest_label = D_IDs
        chunk = pd.DataFrame(data = data_block,
                                  columns = dest_label,
                                  index = sources_label)
        # Convert to minutes, stack 2D array to 1D array
        chunk = chunk.stack(level =-1)
        chunk.columns = ['O','D','DIST']
        return chunk
"""
# Function for performing Euclidian distances.
def EuclidCall(source_list,dest_list,source_points,dest_points):
        distmatrix = np.zeros((len(source_points),len(dest_points)))
        for s in range(0,len(source_points)):
                for d in range(0,len(dest_points)):
                        # 100 included as normalisation factor to MapBox / OSRM results
                        distmatrix[s,d] = (source_points[s].distance(dest_points[d])*100)
        df = pd.DataFrame(data = distmatrix,
                                  columns = dest_list,
                                  index = source_list)
        df = df.stack(level =-1)
        df.columns = ['O','D','DIST']
        return df
"""
# Generate appropriately split source and destination lists
def split_and_bundle(in_list,break_size):
        new_list = []
        for i in range (0,(int(max(len(in_list)/break_size,1)))):
                upper = (i+1) * break_size
                lower = (upper - break_size)
                objs = in_list[lower:upper]
                new_list.append(objs)
        if len(in_list) > break_size:
                rem = len(in_list) % break_size
                if rem > 0:
                        final = upper+rem
                        new_list.append(in_list[upper:final])
        return new_list

if call_type == 'MBT' :
        sources_list = split_and_bundle(source_list, 5)
        dests_list = split_and_bundle(dest_list, 5)
        sources_UIDs = split_and_bundle(source_UIDs, 5)
        dests_UIDs = split_and_bundle(dest_UIDs, 5)
elif call_type == 'MB'or call_type == 'OSRM':
        sources_list = split_and_bundle(source_list, 12)
        dests_list = split_and_bundle(dest_list, 13)
        sources_UIDs = split_and_bundle(source_UIDs, 12)
        dests_UIDs = split_and_bundle(dest_UIDs, 13)
else:
        pass

# Run function call across the O-D matrix; output is 'df'
returns = []
numcalls = (len(sources_list) * len(dests_list))
s , d = sources_list, dests_list
i, j = 1 + (rescue * len(sources_list)), 1 + rescue

if call_type == 'Euclid':
        df = EuclidCall(source_list,dest_list,source_points,dest_points)
else:
        if rescue > 0:
                s = s[rescue:] # possibly rescue -1
                sources_UIDs = sources_UIDs[rescue:]
        print('source list: %s' % len(source_list))
        print('sources list: %s' % len(sources_list))
        print('dest list: %s' % len(dest_list))
        print('dests list: %s' % len(dests_list))
        numcalls_rem = (len(s) * len(d))
        print('\nEstimated remaining calls to chosen server: %d\n' % numcalls_rem)
        print('save points will occur every %d calls\n' % (len(dests_list)))
        time.sleep(5)
        for O_list in s:
                O_IDs = sources_UIDs[s.index(O_list)]
                for D_list in d:
                        #try:
                        if call_type == 'MBT' :
                                time.sleep(2)
                        else:
                                time.sleep(1)
                        D_IDs = dests_UIDs[d.index(D_list)]
                        if call_type == 'MB':
                                returns.append(MapboxCall(O_list,D_list,i,O_IDs,D_IDs))
                        elif call_type == 'MBT':
                                returns.append(MapboxCallTraffic(O_list,D_list,i,O_IDs,D_IDs))
                        elif call_type == 'OSRM':
                                returns.append(OSRMCall(O_list,D_list,i,O_IDs,D_IDs))
                        i += 1

                        #except:
                                #save_current(O_list, D_list)
                save(returns, j, i, numcalls, rescue_num)
                j += 1
        try:
                df = pd.concat(returns)
        except:
                df = returns

# re-attach the population of origins and destinations, prep dataframe
all_matrices = []
if rescue_num > 0:
        for r in range(0,rescue_num):
                rescued_matrix = pd.read_csv(os.path.join(ffpath,'temp_file_%d.csv' % (r)),header=None)
                rescued_matrix.columns = ['O_UID','D_UID','DIST']
                all_matrices.append(rescued_matrix)
df = df.reset_index()
df.columns = ['O_UID','D_UID','DIST']
all_matrices.append(df)
new = pd.concat(all_matrices)
new = new.set_index('O_UID')
new['DIST'] = new['DIST'].apply(pd.to_numeric)
popdf = input_df[[UID,Pop]].set_index(UID)
new['O_POP'] = popdf[Pop]
new = new.reset_index()
new = new.set_index('D_UID')
if dest_list == source_list:
        new['D_POP'] = popdf[Pop]
        new = new.reset_index()
else:
        popdf_dest = input_df2[[UID,Pop]].set_index(UID)
        new['D_POP'] = popdf_dest[Pop]
        new = new.reset_index()
new['O_UID'] = new['O_UID'].astype(str)
new['D_UID'] = new['D_UID'].astype(str)
new['combo'] = new['O_UID']+'_X_'+new['D_UID']
new = new.drop_duplicates('combo')
new = new.drop(['combo'], axis = 1)
outpath = os.path.join(ffpath, 'Output')
if not os.path.exists(outpath):
        os.mkdir(os.path.join(ffpath, 'Output'))
new.to_csv(os.path.join(outpath, 'Pairs.csv'))

###### Market Access ######
# Define a range of lambas - the distance sensitivity factor for market access
lambder_list = [0.01,
                0.005,
                0.001,
                0.0007701635,   # Market access halves every 15 mins
                0.0003850818,   # Market access halves every 30 mins
                0.0001925409,   # Market access halves every 60 mins
                0.0000962704,   # Market access halves every 120 mins
                0.0000385082,   # Market access halves every 300 mins
                0.00001]

# Run market access for all lambda across 'new' dataframe
output = pd.DataFrame()
new = new.loc[new['DIST'] > -1]
def market_access(x,lambdar):
    return sum(x.D_POP*np.exp(-lambdar*x.DIST))
for lamdar in lambder_list:
    output[lamdar] = new.loc[new['DIST'] > 0].groupby('O_UID').apply(lambda x:market_access(x,lamdar))

#File output, print completion time
output.to_csv(os.path.join(outpath, 'Output.csv'))
readmetext = ("""
        GOST: Market Access: Product Assumptions

        Last Updated: 9 Feb 2018
        Programmer: C. Fox
        Theory: K. Garrett, T. Norman

        This GOST Market Access product is based off of:
                - Mapbox's Matrix API for travel times;
                - OSRM's API for travel times

        Travel Time Calculation

        The Mapbox Matrix API provides estimated trip durations in seconds.
        The time it takes to travel from one point to another is determined by a
        number of factors, including:
        - The profile used (walking, cycling, or driving); (GOST: set to driving)
        - The speed stored in the maxspeed tag in OpenStreetMap
          (https://wiki.openstreetmap.org/wiki/Key:maxspeed)
        - Traffic derived from real-time telemetry data, provided by Mapbox

        Traffic data

        In addition to the contributions of OpenStreetMap, Mapbox SDKs collect
        anonymous data, or telemetry, about devices using their services to continuously
        update their routing network. Attributes such as speed, turn restrictions, and
        travel mode can be collected to improve OpenStreetMap.

        Advanced - Speed Assumptions

        See https://github.com/Project-OSRM/osrm-backend/blob/master/docs/profiles.md
        For a full explanation of profiles, and how speeds are calculated across segments

        Note on API request timings

        Requests using mapbox/driving, mapbox/walking, and mapbox/cycling profiles
        can specify up to 25 input coordinates per request. Requests using the
        mapbox/driving-traffic profiles can specify up to 10 input coordinates per request.

        Requests using mapbox/driving, mapbox/walking, and mapbox/cycling profiles
        have a maximum limit of 60 requests per minute. Requests using the
        mapbox/driving-traffic profiles have a maximum of 30 requests per minute.

        Algorithm flags

        Commands recognised for this script:
        -p   Path - string for input and output folder path
        -f   File name of .csv containing input data
        -m   Latitude column name.
        -n   Longitude column name
        -o   Origin Unique Identifier column name (e.g. District, Name, Object ID...).
             This is mainly helpful for joining the output back to the input data / a shapefile,
             and is non-essential in terms of the calculation. It can be text or a number.
        -q   Population / weighting column name
        -c   Server call type - "OSRM" for OSRM, "MB" for Mapbox, "MBT" for Mapbox traffic, or "Euclid" for Euclidean distances (as the crow flies)
        -l   Limit - use this to limit the coordinate input list (int). Optional.

        *** Optional - if sources =/= destinations. Note - Unique identifier and Pop column names must remain the same ***
        -W   Filename of destinations csv
        *** Optional - if encountering server errors / internet connectivity instability ***
        -R   Save - input latest save number to pick up matrix construciton process from there.
        -Z   Rescue number parameter - If you have already re-started the download process, denote how many times. First run = 0, restarted once = 1...
        Do NOT put column names or indeed any input inside quotation marks.
        The only exceptions is if the file paths have spaces in them.
        """)

text_file = open(os.path.join(ffpath,"GOST_ReadMe_MarketAccess.txt"), "w")
text_file.write(readmetext)
text_file.close()

print('\nAll processes complete. Check your path for outputs.')
print('Script will now exit.\n')
