#!/usr/bin/env python

"""
*****************
* TKMAP Program *
*****************

TKMAP is HRD's flight track software that has been used to prepare aicraft reconnassaince missions,
including for NOAA's Hurricane Field Program, for several decades. The first documented version of
TKMAP was written by James Franklin (HRD) in Jul/1986, with subsequent updates in Feb/1989, and
Feb/1996. The initial purpose of this software was to provide flight tracks for NOAA G-IV missions.
Sim Aberson (HRD) added capabilities to produce flight tracks for NOAA WP-3D aircraft, specifically
N42 and N43. Other aicraft were eventually added later on. Paul Leighton (HRD) and Jason Dunion
(HRD) also made important modifications, specifically to account for GlobalHawk requiremenets.
Ghassan Alaka (HRD) converted the software from FORTRAN to Python in Mar/2024.

Produce drop/turn information based on input flight track(s),
    e.g., current1.ftk
    This program has been adapted from tkmap.f, which was developed
    by these authors:
        - James Franklin
        - Sim Aberson
        - Paul Leighton
        - Jason Dunion


Adapted By:   Ghassan J. Alaka, Jr.
Date Created: March 18, 2024

Modified By:   Ghassan J. Alaka, Jr.
Date Modified: April 1, 2024

Example call: python tkmap.py

Modification log:
4/1/2024: First production-ready version is complete.
          Upgrading to v1.9.0

"""

__version__ = '1.9.0'


###########################################################
###########################################################
# Import modules
import datetime,os,sys
#print(datetime.datetime.now())
#import math
import argparse
import numpy as np
#print(datetime.datetime.now())


###########################################################
###########################################################
def TKMAP(MAXTRAX=4, DO_PLOT=True, DO_HTML=True, WestHS=True, UPDATE_STM_CENTER=True, UPDATE_SRLATLON=True, verbose=0):
    """ PROGRAM TKMAP

TKMAP calculates flight track way points and creates text/visual products.
It consists of three modules:
    1) TRACKDIS:     Calculate the flight track distance and time
    2) MAKE_GRAPHIC: Create a static PNG image of one or more flight tracks
    3) WRITE_HTML:   Create an HTML file to visualize and modify each flight track.

    @kwarg MAXTRAX (integer):           Max number of flight tracks
    @kwarg DO_PLOT (boolean):           Produce PNG file
    @kwarg DO_HTML (boolean):           Produce HTML file
    @kwarg WestHS (boolean):            West hemisphere
    @kwarg UPDATE_STM_CENTER (boolean): Update the storm center position
    @kwarg UPDATE_SRLATLON (boolean):   Update storm-relative positions
    @kwarg verbose (integer):           Verbosity (0=none, 1=some, 2=most, 3=all)

    Output files:
        > turns[NF].txt:    Formatted ASCII text with all turn points
        > drops[NF].txt:    Formatted ASCII text with all drop points
        > points[NF]:       Lat/lon for all points
        > points_extra[NF]: Lat/lon plus drop/turn info (1-True, 0-False) for all points
        > hurrloc[NF]:      TC location
        > tkmap1.png:       Static image of 1+ flight tracks
        > tkmap1.html:      HTML file to visualize and modify all points

    """

    print(f'MSG: Program TKMAP started at {datetime.datetime.now()}')

    FLIST = []
    NTRAX = 0
    for NF in range(1,MAXTRAX+1):
        FNAME = f'current{NF}.ftk'
        if os.path.isfile(FNAME):
            print(f'MSG: Processing {FNAME}')
            FLIST.append(FNAME)
            TRACKDIS(NF, FNAME, WestHS=WestHS, UPDATE_STM_CENTER=UPDATE_STM_CENTER, UPDATE_SRLATLON=UPDATE_SRLATLON, verbose=verbose)
            NTRAX=NTRAX+1
    if NTRAX == 0:
        print('ERROR: Did not find any flight tracks to process, e.g., current1.ftk')
        sys.exit(1)


    if DO_PLOT:
        MAKE_GRAPHIC(NTRAX)

    if DO_HTML:
        for N in range(1,NTRAX+1):
            WRITE_HTML(N)

    print(f'MSG: Program TKMAP completed at {datetime.datetime.now()}')



###########################################################
###########################################################
def TRACKDIS(NF, FNAME, WestHS=True, UPDATE_STM_CENTER=True, UPDATE_SRLATLON=True, verbose=0):
    """
    Calculate the flight track distance and flight time from input flight track
file (current[NF].ftk). The input flight track file should contain information
about the aircraft, starting and ending station/base, important way points
(turn/drop points, turn-only points, drop-only points), and, optionally,
information about the storm of interest.

    @param NF:      File number
    @param FNAME:   File name
    @kwarg WestHS:  Boolean for western hemisphere (True)
    @kwarg verbose: Verbosity (0=least,1=some,2=most,3=all)

    Output files:
        > turns[NF].txt:    Formatted ASCII text with all turn points
        > drops[NF].txt:    Formatted ASCII text with all drop points
        > points[NF]:       Lat/lon for all points
        > points_extra[NF]: Lat/lon plus drop/turn info (1-True, 0-False) for all points
        > hurrloc[NF]:      TC location

    """

    print(f'MSG: Module TRACKDIS started at {datetime.datetime.now()}')

    # Define variables
    NM2km = np.float128(111.12)/np.float128(60.)
    globalhawk = False
    climb = False
    ipset = True
    next_line = '\n'
    insert = 0
    altitude_dflt = 10000.  # Just in case, but Gus/Sim decided not to use


    # Define output file names
    FOUT_TURNS = f'turns{NF}.txt'
    FOUT_DROPS = f'drops{NF}.txt'
    FOUT_POINTS = f'points{NF}'
    FOUT_EXTRA = f'points_extra{NF}'
    FOUT_HLOC = f'hurrloc{NF}'


    # Read flight track input
    with open(FNAME, 'r') as f:

        # Read 1st line for info about aircraft, takeoff, and storm
        line = f.readline()
        print(line)
        line_split = line.split()
        if len(line_split) == 2:
            iac, takeoff, stmname = int(line_split[0]), line_split[1].strip(), 'UNKNOWN'
        elif len(line_split) == 3:
            iac, takeoff, stmname = int(line_split[0]), line_split[1].strip(), ' '.join([l.strip() for l in line_split[2:]])
        else:
            print(f'ERROR: The 1st line of {FNAME} must have 2 or 3 columns. Found {len(line_split)}')
            sys.exit(1)
        print(f'Aircraft: {iac},  Takeoff:  {takeoff},  Storm: {stmname}')

        # Determine base speed at altitude
        SPEED, ialt1, ialt2, globalhawk = AIRCRAFT_DFLT(iac)
        print(f'Aicraft {iac} has these base specifications:')
        print(f'    speed={SPEED}, typical altitude range is {ialt1*1000}-{ialt2*1000} ft')
        print(f'    Non-included drops to turns (globalhawk option)? {globalhawk}')


        # Read the rest of the lines
        BASELIST, IPOS = [], []
        TYPELIST, LATLIST, LONLIST, ALTLIST, INSERTLIST = [], [], [], [], []
        SRRADLIST, SRAZMLIST, SPEEDLIST,  TURNLIST, DROPLIST = [], [], [], [], []
        FLAG = []
        for i,line in enumerate(f):
            if line.isspace():  continue
            print(line)


            # Advance 1 step. Append new entries to all lists
            line_split = line.split()
            FLAG.append(' ')
            SPEEDLIST.append(SPEED)
            TYPELIST.append(None)
            LATLIST.append(None)
            LONLIST.append(None)
            ALTLIST.append(None)
            SRRADLIST.append(-99)
            SRAZMLIST.append(None)
            INSERTLIST.append(None)
            TURNLIST.append(None)
            DROPLIST.append(None)


            # H: Storm info, including location and motion.
            #    Not included in turns or drops.
            if line_split[0].strip() == 'H':
                stmlat, stmlon = np.float128(line_split[1].strip()), np.float128(line_split[2].strip())
                if len(line_split) > 3:
                    stmdir, stmspd = np.float128(line_split[3].strip()), np.float128(line_split[4].strip())
                else:
                    stmdir, stmspd = np.float128(0.0), np.float128(0.0)
                stmu, stmv = UVCOMP(stmdir, stmspd)
                if verbose >= 2:  print(f'stmu,v = {stmu}, {stmv}')
                TYPELIST[i] = line_split[0].strip()
                LATLIST[i] = stmlat
                # Add storm longitude to LONLIST with the appropriate sign
                if WestHS:  LONLIST[i] = -stmlon
                else:       LONLIST[i] = stmlon
                TURNLIST[i] = False
                DROPLIST[i] = False
                file1 = open(FOUT_HLOC, "w")
                file1.write(f'   {LATLIST[i]:.7f}     {abs(LONLIST[i]):3.7f}{next_line}')
                file1.close()
                print(f'MSG: Created output: {FOUT_HLOC}')


            # A: Takeoff site. Included in turns. No drop.
            # Z: Recovery site. Included in turns. No drop.
            elif line_split[0].strip() in ['A','Z']:
                BASE = ' '.join([l.strip() for l in line_split[1:]])
                BLAT, BLON = CITY_LOCATION(BASE)
                BASELIST.append(BASE)
                TYPELIST[i] = line_split[0].strip()
                LATLIST[i] = np.float128(BLAT)
                LONLIST[i] = np.float128(BLON)
                ALTLIST[i] = np.float128(0.)
                TURNLIST[i] = True
                DROPLIST[i] = False
                IPOS.append(i)
                if verbose >= 1:  print(f'{i}: flag={TYPELIST[i]}; xlat={LATLIST[i]}; xlon={LONLIST[i]}; altitude={ALTLIST[i]}')


            # S: Storm-relative locations (storm location provided by 'H' line).
            #    Included in turns and drops.
            elif line_split[0].strip() == 'S':
                rdis, theta = np.float128(line_split[1].strip()), np.float128(line_split[2].strip())
                try:
                    ALTLIST[i] = np.float128(line_split[3].strip())
                except:
                    print('ERROR: Altitude not found in this line --> {line}')
                    print('ERROR: Please enter a valid altitude!')
                    sys.exit(2)
                    #ALTLIST[i] = np.float128(altitude_dflt)
                if iac in [42,43,57] and i > 2:
                    SPEEDLIST[i] = GETSPEED(iac,ALTLIST[i])
                TYPELIST[i] = line_split[0].strip()
                if WestHS:  xlat, xlon = SRLATLON(stmlat, -stmlon, theta, rdis*NM2km)
                else:       xlat, xlon = SRLATLON(stmlat, stmlon, theta, rdis*NM2km)
                LATLIST[i] = xlat
                LONLIST[i] = xlon
                FLAG[i] = 'S'
                SRRADLIST[i] = rdis
                SRAZMLIST[i] = theta
                TURNLIST[i] = True
                DROPLIST[i] = True
                insert = 0
                if verbose >= 1:  print(f'{i}: flag={TYPELIST[i]}; xlat={LATLIST[i]}; xlon={LONLIST[i]}; altitude={ALTLIST[i]}')


            # I: Flag to add intermediate drops between way points (previous and next lines)
            #    Included in drops. Not included in turns.
            #    Intermediate drops will be added later (after file completely read).
            elif line_split[0].strip() == 'I':
                try:
                    ALTLIST[i] = np.float128(line_split[2].strip())
                except:
                    print('ERROR: Altitude not found in this line --> {line}')
                    print('ERROR: Please enter a valid altitude!')
                    sys.exit(2)
                    #ALTLIST[i] = np.float128(altitude_dflt)
                insert = int(line_split[1].strip())
                INSERTLIST[i] = insert
                if iac in [42,43,57] and i > 2:  # Why i > 2?
                    SPEEDLIST[i] = GETSPEED(iac, ALTLIST[i])
                FLAG[i] = 'I'
                TYPELIST[i] = line_split[0].strip()
                TURNLIST[i] = False
                DROPLIST[i] = True
                if verbose >= 1:  print(f'{i}: flag={TYPELIST[i]}; altitude={ALTLIST[i]}')


            # T: Turn point without a drop
            elif line_split[0].strip() == 'T':
                LATLIST[i] = np.float128(line_split[1].strip())
                LONLIST[i] = -np.float128(line_split[2].strip())
                try:
                    ALTLIST[i] = np.float128(line_split[3].strip())
                except:
                    print('ERROR: Altitude not found in this line --> {line}')
                    print('ERROR: Please enter a valid altitude!')
                    sys.exit(2)
                    #ALTLIST[i] = np.float128(altitude_dflt)
                TURNLIST[i] = True
                DROPLIST[i] = False
                TYPELIST[i] = line_split[0].strip()
                if iac in [42,43,57] and i > 2:
                    SPEEDLIST[i] = GETSPEED(iac,ALTLIST[i])
                insert = 0
                if verbose >= 1:  print(f'{i}: flag={TYPELIST[i]}; xlat={LATLIST[i]}; xlon={LONLIST[i]}; altitude={ALTLIST[i]}')


            # C: Unknown option. Altitude change?
            elif line_split[0].strip() == 'C':
                i=i-1
                ialt1, ialt2 = np.float128(line_split[1].strip()), np.float128(line_split[2].strip())


            # E: Unknown option
            # F: Unknown option
            elif line_split[0].strip() in ['E', 'F']:
                FLAG[i] = 'E'


            # ' ': Blank first character indicates lat/lon location (not storm-relative)
            #      Included in turns and drops.
            else:
                LATLIST[i] = np.float128(line_split[0].strip())
                LONLIST[i] = -np.float128(line_split[1].strip())
                try:
                    ALTLIST[i] = np.float128(line_split[2].strip())
                except:
                    print('ERROR: Altitude not found in this line --> {line}')
                    print('ERROR: Please enter a valid altitude!')
                    sys.exit(2)
                    #ALTLIST[i] = np.float128(altitude_dflt)
                TURNLIST[i] = True
                DROPLIST[i] = True
                if iac in [42,43,57] and i > 2:
                    SPEEDLIST[i] = GETSPEED(iac,ALTLIST[i])
                insert = 0
                if verbose >= 1:  print(f'{i}: flag={TYPELIST[i]}; xlat={LATLIST[i]}; xlon={LONLIST[i]}; altitude={ALTLIST[i]}')



    # Add intermediate drop points between way points ("I")
    j = 0
    TYPELIST_ORIG = TYPELIST.copy()
    for i,flg in enumerate(TYPELIST_ORIG):
        if flg == 'I':
            insert = INSERTLIST[j]
            lat_range = LATLIST[j+1] - LATLIST[j-1]
            lon_range = LONLIST[j+1] - LONLIST[j-1]
            dlat = lat_range/np.float128(insert+1)
            dlon = lon_range/np.float128(insert+1)
            LATLIST[j] = LATLIST[j-1] + dlat
            LONLIST[j] = LONLIST[j-1] + dlon
            TURNLIST[j] = False
            DROPLIST[j] = True
            k = j+insert
            j=j+1
            while j < k:
                LATLIST.insert(j, LATLIST[j-1] + dlat)
                LONLIST.insert(j, LONLIST[j-1] + dlon)
                TURNLIST.insert(j, False)
                DROPLIST.insert(j, True)
                ALTLIST.insert(j, ALTLIST[j-1])
                if iac in [42,43,57] and i > 2:
                    SPEEDLIST.insert(j, GETSPEED(iac,ALTLIST[j]))
                else:
                    SPEEDLIST.insert(j, SPEEDLIST[j-1])
                TYPELIST.insert(j, 'I')
                INSERTLIST.insert(j, None)
                SRRADLIST.insert(j, SRRADLIST[j-1])
                SRAZMLIST.insert(j, SRAZMLIST[j-1])
                FLAG.insert(j, 'I')
                j=j+1

        else:
            j=j+1



    # Write header information to output files
    LUFO = open(FOUT_TURNS, 'w')
    LUFO.write(' ========================================================================\n')
    LUFO.write(f' MISSION PLAN:  {stmname.upper()}{next_line}{next_line}')
    LUFO.write(f' Prepared by the Hurricane Research Division File: {FNAME}{next_line}{next_line}')
    LUFO.write(f' Aircraft: N{iac}RF  Proposed takeoff: {takeoff}{next_line}')
    LUFO.write(' ========================================================================\n\n\n')
    LUFO.write(' TRACK DISTANCE TABLE\n\n')
    LUFO.write(' ===========================================================\n')
    LUFO.write('  #      LAT      LON     RAD/AZM     LEG    TOTAL     TIME\n')
    LUFO.write('        (d m)    (d/m)    (NM/dg)     (NM)   (NM)     (h:mm)\n')
    LUFO.write(' -----------------------------------------------------------\n')
    LUFO.close()

    LUT = open(FOUT_DROPS, 'w')
    LUT.write(' ========================================================================\n')
    LUT.write(f' MISSION PLAN:  {stmname.upper()}{next_line}{next_line}')
    LUT.write(f' Prepared by the Hurricane Research Division File: {FNAME}{next_line}{next_line}')
    LUT.write(f' Aircraft: N{iac}RF  Proposed takeoff: {takeoff}{next_line}')
    LUT.write(' ========================================================================\n\n\n')
    LUT.write(' DROP LOCATIONS\n\n')
    LUT.write(' ==========================================\n')
    LUT.write('  #      LAT      LON      RAD/AZM    TIME\n')
    LUT.write('        (d m)    (d m)     (NM/dg)   (h:mm)\n')
    LUT.write(' ------------------------------------------\n')
    LUT.close()

    LUP = open(FOUT_POINTS, 'w')
    LUP.close()

    LUPE = open(FOUT_EXTRA, 'w')
    LUPE.close()

    # Step through all of the points to compute flight track information & statistics
    LTURN = -1
    IC = 0
    LDROP = 0       #  jpd changed from “1” to “0” to set IP as waypoint #1: 6-10-2016
    TOTAL = np.float128(0.0)
    SUBTOTAL = np.float128(0.0)  # pal keeps track of legs of inserted drops.
    TIME = np.float128(0.0)
    dleg52 = np.float128(0.0)
    #NT = i
    dleg_accum = np.float128(0.0)

    for i in range(len(TYPELIST)):
        SUBTOTAL = TOTAL
        if TYPELIST[i] in ['X', 'H']:  continue
        IL = IC  # Last index
        IC = i   # Current index
        if IL == 0:  IL = IC
        LTURN = LTURN+1

        if TYPELIST[i] == 'S':
            UPDATE_STM_CENTER=True
            UPDATE_SRLATLON=True
            if UPDATE_STM_CENTER:
                # Guess the new location and the length of the leg
                lat_guess = LATLIST[IC] + TIME*stmv/60.
                lon_guess = LONLIST[IC] + TIME*stmu/(60. * np.cos(np.radians(lat_guess)))
                dleg_guess = GCDISTANCE(lat_guess, lon_guess, LATLIST[IL], LONLIST[IL])
                time_guess = TIME + dleg_guess/SPEEDLIST[i]

                # Calculate storm location at new time
                stmlat_now = stmlat + time_guess*stmv/60.
                stmlon_now = -stmlon + time_guess*stmu/(60. * np.cos(np.radians(stmlat_now)))

                # Update aircraft location
                lat_now, lon_now = SRLATLON(stmlat_now, stmlon_now, SRAZMLIST[IC], SRRADLIST[IC]*111.1/60.)
                dleg = GCDISTANCE(lat_now, lon_now, LATLIST[IL], LONLIST[IL])    
                if UPDATE_SRLATLON:
                    LATLIST[IC], LONLIST[IC] = lat_now, lon_now
            else:
                dleg = GCDISTANCE(LATLIST[IC], LONLIST[IC], LATLIST[IL], LONLIST[IL])
            TOTAL = TOTAL + dleg
            if verbose >= 2:  print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, lat1={LATLIST[IC]}, lat2={ LATLIST[IL]}, lon1={LONLIST[IC]}, lon2={LONLIST[IL]}')
            if verbose >= 3:  print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, time={TIME}, dleg={dleg}, speed={SPEEDLIST[i]}')
            TIME = TIME + dleg/SPEEDLIST[i] + 0.0167
            print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, time={TIME:7.4f}, dleg={dleg:7.2f}, speed={SPEEDLIST[i]}, lat={LATLIST[IC]:5.2f}, lon={LONLIST[IC]:7.2f}')
            SUBTOTAL = SUBTOTAL + dleg

        elif TYPELIST[i] not in ['I', 'D']:
            dleg = GCDISTANCE(LATLIST[IC], LONLIST[IC], LATLIST[IL], LONLIST[IL])
            TOTAL = TOTAL + dleg
            if verbose >= 2:  print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, lat1={LATLIST[IC]}, lat2={ LATLIST[IL]}, lon1={LONLIST[IC]}, lon2={LONLIST[IL]}')
            if verbose >= 3:  print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, time={TIME}, dleg={dleg}, speed={SPEEDLIST[i]}')
            TIME = TIME + dleg/SPEEDLIST[i] + 0.0167
            print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, time={TIME:7.4f}, dleg={dleg:7.2f}, speed={SPEEDLIST[i]}, lat={LATLIST[IC]:5.2f}, lon={LONLIST[IC]:7.2f}')
            SUBTOTAL = SUBTOTAL + dleg

        elif TYPELIST[i] == 'I':
            if iac in [52, 57, 51, 50, 49, 43, 42]:  LTURN = LTURN-1
            dleg = GCDISTANCE(LATLIST[IC], LONLIST[IC], LATLIST[IL], LONLIST[IL])
            dleg52 = dleg52+dleg
            TOTAL = TOTAL + dleg
            SUBTOTAL = SUBTOTAL + dleg
            TIME = TIME + dleg/SPEEDLIST[i]
            print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, time={TIME:7.4f}, dleg={dleg:7.2f}, speed={SPEEDLIST[i]}, lat={LATLIST[IC]:5.2f}, lon={LONLIST[IC]:7.2f}')

        else:
            if iac in [52, 57, 51, 50, 49, 43, 42]:  LTURN = LTURN-1
            dleg = GCDISTANCE(LATLIST[IC], LONLIST[IC], LATLIST[IL], LONLIST[IL])
            dleg52 = dleg52+dleg
            TOTAL = TOTAL + dleg
            SUBTOTAL = SUBTOTAL + dleg
            TIME = TIME + dleg/SPEEDLIST[i]
            print(f'{LTURN:02d}:  TYPE={TYPELIST[i]}, time={TIME:7.4f}, dleg={dleg:7.2f}, speed={SPEEDLIST[i]}, lat={LATLIST[IC]:5.2f}, lon={LONLIST[IC]:7.2f}')


        # Global Hawk special considerations
        if iac == 52:
            # jpd  modified to add 30-min to the GH track after take-off (GH climb-out maneuvers)
            if TYPELIST[i] == 'A':  climb = True

            # jpd  modified to add 30-min to the GH track just before landing (GH descent maneuvers)
            elif TYPELIST[i] == 'Z':
                TIME = TIME + 0.5
                dleg = dleg + (335*0.5)
                TOTAL = TOTAL + (335*0.5)

        # Calculate degrees/minutes and hours/minutes
        LAD, LAM = DGMN(LATLIST[i])
        LOD, LOM = DGMN(LONLIST[i])
        ITH, ITM = DGMN(TIME)
        if verbose >= 2:  print(f'{LTURN:02d} lat={LATLIST[i]} --> {LAD} {LAM}')
        if verbose >= 2:  print(f'{LTURN:02d} lon={LONLIST[i]} --> {LOD} {LOM}')
        if verbose >= 2:  print(f'{LTURN:02d} time={TIME} --> {ITH} {ITM}')

        IX = 0
        for L, IP in enumerate(IPOS):
            if IP == i:  IX = L

        LUP = open(FOUT_POINTS, 'a')
        LUPE = open(FOUT_EXTRA, 'a')
        if DROPLIST[i] or TURNLIST[i]:
            if TYPELIST[i] != 'T':
                LUP.write(f'  {LATLIST[i]:3.3f} {abs(LONLIST[i]):4.3f}{next_line}')
            else:
                LUP.write(f'  {LATLIST[i]:3.3f} {abs(LONLIST[i]):4.3f} T{next_line}')
        IDROP = 1 if DROPLIST[i] else 0
        ITURN = 1 if TURNLIST[i] else 0
        LUPE.write(f'  {LATLIST[i]:3.3f} {LONLIST[i]:4.3f} {ITURN} {IDROP}{next_line}')
        LUP.close()

        if ( LTURN == 1 or LDROP == 1 ) and ipset:
            IPH, IPM, ipset = ITH, ITM, False

        if TYPELIST[i] != 'D' or not globalhawk:
            dlegout = SUBTOTAL
            if TYPELIST[i] == 'I':
                dleg_accum = dleg_accum + dleg
                if verbose >= 1:  print(f'dleg_accum={dleg_accum}')
            else:
                if dleg_accum > 0:
                    print(f'Resetting dleg to dleg+dleg_accum={dleg+dleg_accum}')
                    dleg = dleg + dleg_accum
                    dleg_accum = np.float128(0.0)
            if iac in [52, 57, 51, 50, 49, 43, 42]:
                dleg = dleg + dleg52
                dleg52 = np.float128(0.0)
            if LTURN == 1 and iac == 52:
                dleg = dleg + 335*0.5
                TOTAL = TOTAL + (335*0.5)
            LUFO = open(FOUT_TURNS, 'a')
            if TURNLIST[i]:
                if TYPELIST[i] in ['A', 'Z']:
                    LUFO.write(f' {LTURN:2d}{FLAG[i]}    {BASELIST[IX]:<29}{dleg:4.0f}.   {TOTAL:4.0f}.    {ITH:2d}:{ITM:02d}{next_line}')
                elif SRRADLIST[i] >= 0:
                    LUFO.write(f' {LTURN:2d}{FLAG[i]}    {LAD:2d} {LAM:02d}  {abs(LOD):4d} {LOM:02d}    {int(SRRADLIST[i]):3d}/{int(SRAZMLIST[i]):03d}    {dleg:4.0f}.   {TOTAL:4.0f}.    {ITH:2d}:{ITM:02d}{next_line}')
                else:
                    LUFO.write(f' {LTURN:2d}{FLAG[i]}    {LAD:02d} {LAM:02d}  {abs(LOD):4d} {LOM:02d}               {dleg:4.0f}.   {TOTAL:4.0f}.    {ITH:2d}:{ITM:02d}{next_line}')
            LUFO.close()
            SUBTOTAL = np.float128(0.0)

        if iac == 52 and climb:
            TIME = TIME + 0.5
            climb = False

        if TYPELIST[i] in [' ', 'D', 'E', 'S', 'I'] or TYPELIST[i] is None:
            LDROP = LDROP+1
            if ( LTURN == 1 or LDROP == 1) and ipset:
                IPH, IPM, ipset = ITH, ITM, False
            LUT = open(FOUT_DROPS, 'a')
            if DROPLIST[i]:
                if SRRADLIST[i] >= 0:
                    LUT.write(f' {LDROP:2d}{FLAG[i]}   {LAD:3d} {LAM:02d}  {abs(LOD):4d} {LOM:02d}     {int(SRRADLIST[i]):3d}/{int(SRAZMLIST[i]):03d}   {ITH:2d}:{ITM:02d}{next_line}')
                else:
                    LUT.write(f' {LDROP:2d}{FLAG[i]}   {LAD:3d} {LAM:02d}  {abs(LOD):4d} {LOM:02d}               {ITH:2d}:{ITM:02d}{next_line}')
            LUT.close()


    # Write footers and close output files
    LUFO = open(FOUT_TURNS, 'a')
    LUFO.write(' -----------------------------------------------------------\n\n\n')
    LUFO.write(' ************************************************************************\n')
    LUFO.write(f' MISSION PLAN:  {stmname.upper()}{next_line}')
    LUFO.write(f' Prepared by the Hurricane Research Division File: {FNAME}{next_line}')
    LUFO.write(f' Aircraft: N{iac}RF{next_line}')
    LUFO.write(f' Proposed takeoff: {BASELIST[0]}  {takeoff}{next_line}')
    LUFO.write(f' Proposed recovery: {BASELIST[-1]}{next_line}')
    LUFO.write(f' Time to IP:  {IPH:1d}:{IPM:02d}{next_line}')
    LUFO.write(f' Mission Duration: {ITH:2d}:{ITM:02d}{next_line}')
    LUFO.write(' ************************************************************************\n')
    LUFO.close()

    LUT = open(FOUT_DROPS, 'a')
    LUT.write(' ------------------------------------------\n')
    LUT.close()

    #LUP.close()

    print(f'MSG: Created output: {FOUT_HLOC}')
    print(f'MSG: Created output: {FOUT_POINTS}')
    print(f'MSG: Created output: {FOUT_EXTRA}')
    print(f'MSG: Created output: {FOUT_TURNS}')
    print(f'MSG: Created output: {FOUT_DROPS}')

    print(f'MSG: Module TRACKDIS completed at {datetime.datetime.now()}')



###########################################################
###########################################################
def MAKE_GRAPHIC(NT):
    """
    Produce a static graphic based on the output(s) from TRACKDIS. The outputs
are explicitly re-read, rather than passed as input arguments to this module. The
graphic is produced using MatPlotLib and the map is created with Cartopy.

    @param NT:  Number of individual tracks (could be 1)

    Output files:
        > tkmap1.png:       Static image of 1+ flight tracks

    """
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib import pyplot as plt

    print(f'MSG: Module MAKE_GRAPHIC started at {datetime.datetime.now()}')

    lats, lons = [], []
    IS_TURN, IS_DROP = [], []
    for N in range(1,NT+1):
        # Get turn, drop, and TC information
        track_data = np.loadtxt(f'points_extra{N}')
        #if FORCE_WH:
        #    tk_points[:,1] = -1.*tk_points[:,1]
        lats.append(track_data[:,0])
        lons.append(track_data[:,1])
        IS_TURN.append([True if i == 1 else False for i in track_data[:,2]])
        IS_DROP.append([True if i == 1 else False for i in track_data[:,3]])
    #print(track_data)
    #print(IS_TURN, IS_DROP)
    with open('turns1.txt', 'r') as fd:
        all_lines = fd.readlines()
        mission_info = all_lines[1]+all_lines[5][:-1]
    stn_0012 = np.loadtxt('stnlist0012')
    stn_00 = np.loadtxt('stnlist00')
    stn_12 = np.loadtxt('stnlist12')
    hurrloc = np.loadtxt('hurrloc1')

    # Determine map boundaries based on data
    lat_max, lat_min = np.max([np.max(A) for A in lats]), np.min([np.min(A) for A in lats])
    lat_ctr = (lat_max + lat_min)/2.
    lon_max, lon_min = np.max([np.max(A) for A in lons]), np.min([np.min(A) for A in lons])
    lon_ctr = (lon_max + lon_min)/2.
    lat_span, lon_span = np.abs(lat_max-lat_min), np.abs(lon_max-lon_min)
    map_ctr = [lat_ctr, lon_ctr]
    map_span = 1.5*np.max([lon_span, lat_span])
    #map_limits = [lat_ctr+0.5*map_span, lat_ctr-0.5*map_span, lon_ctr+0.5*map_span, lon_ctr-0.5*map_span]
    map_limits = [[lat_ctr-0.5*map_span, lon_ctr-0.5*map_span], [lat_ctr+0.5*map_span, lon_ctr+0.5*map_span]]
    #print(map_limits)
  
  
    ##########
    # CREATE A STATIC FIGURE
  
    # Create cartopy objects for map features of interest
    resol = '10m'  # use data at this scale
    bodr = cfeature.NaturalEarthFeature(category='cultural',
      name='admin_0_boundary_lines_land', scale=resol, facecolor='none', alpha=0.7)
    bodr2 = cfeature.NaturalEarthFeature(category='cultural',
      name='admin_1_states_provinces_lines', scale='50m', facecolor='none', alpha=0.7)
    land = cfeature.NaturalEarthFeature('physical', 'land', \
      scale=resol, edgecolor='k', facecolor=cfeature.COLORS['land'])
    ocean = cfeature.NaturalEarthFeature('physical', 'ocean', \
      scale=resol, edgecolor='none', facecolor=cfeature.COLORS['water'])
    lakes = cfeature.NaturalEarthFeature('physical', 'lakes', \
      scale=resol, edgecolor='b', facecolor=cfeature.COLORS['water'])
    rivers = cfeature.NaturalEarthFeature('physical', 'rivers_lake_centerlines', \
      scale=resol, edgecolor='b', facecolor='none')
  
    # Create figure
    ft_colors = ['go-', 'mo-', 'yo-']
    fig1 = plt.Figure(figsize=(10,10), dpi=1000)
    ax1 = fig1.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax1.set_xlim([map_limits[0][1], map_limits[1][1]])
    ax1.set_ylim([map_limits[0][0], map_limits[1][0]])
    ax1.gridlines(draw_labels=True)
    #ax1.coastlines()
    #ax1.add_feature(cfeature.STATES, linestyle=':', edgecolor='black', linewidth=0.5)
    ax1.add_feature(land, facecolor='beige')
    ax1.add_feature(ocean, linewidth=0.2 )
    ax1.add_feature(lakes)
    ax1.add_feature(rivers, linewidth=0.5)
    ax1.add_feature(bodr, linestyle='--', edgecolor='k', alpha=1)
    ax1.add_feature(bodr2, linestyle=':', linewidth=0.5, edgecolor='k', alpha=1)
    #ax1.scatter(tk_points[:,1], tk_points[:,0], marker='o', color='r', size=10, transform=ccrs.PlateCarree(), zorder=3)
    ax1.scatter(stn_0012[:,1], stn_0012[:,0], marker='^', color='r', s=50, transform=ccrs.PlateCarree(), zorder=3)
    ax1.scatter(stn_00[:,1], stn_00[:,0], marker='^', color='cyan', s=50, transform=ccrs.PlateCarree(), zorder=3)
    ax1.scatter(stn_12[:,1], stn_12[:,0], marker='^', color='purple', s=50, transform=ccrs.PlateCarree(), zorder=3)
    for j, (latx, lonx) in enumerate(zip(lats, lons)):
        for i, (x, y) in enumerate(zip(lonx[:], latx[:])):
            ax1.plot(lonx[i-1:i+1], latx[i-1:i+1], ft_colors[j], linewidth=4, markersize=10, zorder=3)
            ax1.text(x+0.005*map_span, y+0.005*map_span, f'{i}', size=14, zorder=5)
  
    ax1.scatter(0.03, 0.13, marker='^', color='r', s=50, zorder=3, transform=ax1.transAxes)
    ax1.scatter(0.03, 0.08, marker='^', color='cyan', s=50, zorder=3, transform=ax1.transAxes)
    ax1.scatter(0.03, 0.03, marker='^', color='purple', s=50, zorder=3, transform=ax1.transAxes)
    ax1.text(0.05, 0.12, '00 and 12 UTC Rawinsonde', size=16, color='r', transform=ax1.transAxes)
    ax1.text(0.05, 0.07, '00 UTC Rawinsonde', size=16, color='cyan', transform=ax1.transAxes)
    ax1.text(0.05, 0.02, '12 UTC Rawinsonde', size=16, color='purple', transform=ax1.transAxes)
  
    fig1.suptitle(f'FLIGHT TRACK\n{mission_info}', size=24, fontweight='bold')
    fig1.tight_layout()
    fig1.savefig(f'tkmap1.png')

    print(f'MSG: Created output: tkmap1.png')

    print(f'MSG: Module MAKE_GRAPHIC completed at {datetime.datetime.now()}')



###########################################################
###########################################################
def WRITE_HTML(N):
    """
    Produce an HTML file that allows dynamic visualization of each
flight track. Build the file piece by piece to inject information
specific to a particular flight track.

    @param N:  the flight track number

    Output files:
        > tkmap[N].html: HTML file to visualize and modify all points
    """

    print(f'MSG: Module WRITE_HTML started at {datetime.datetime.now()}')

    next_line = '\n'
    squote = '\''
    sbracket = '{'
    ebracket = '}'

    # Get turn, drop, and TC information
    track_data = np.loadtxt(f'points_extra{N}')
    #if FORCE_WH:
    #    tk_points[:,1] = -1.*tk_points[:,1]
    lats = track_data[:,0]
    lons = track_data[:,1]
    IS_TURN = [True if i == 1 else False for i in track_data[:,2]]
    IS_DROP = [True if i == 1 else False for i in track_data[:,3]]
    #print(track_data)
    #print(IS_TURN, IS_DROP)
    with open('turns1.txt', 'r') as fd:
        mission_info = fd.readlines()[5]
    stn_0012 = np.loadtxt('stnlist0012')
    stn_00 = np.loadtxt('stnlist00')
    stn_12 = np.loadtxt('stnlist12')
    hurrloc = np.loadtxt('hurrloc1')

    HTML_FILE = open(f'tkmap{N}.html', 'w')

    HTML1 = """<!DOCTYPE html>
<html>
<head>
    
    <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
    <!-- <link rel="stylesheet" href="style.css"/> -->
    
        <script>
            L_NO_TOUCH = false;
            L_DISABLE_3D = false;
        </script>
    
    <style>html, body {width: 100%;height: 100%;margin: 0;padding: 0;}</style>
    <style>#map {position:absolute;top:0;bottom:0;right:0;left:0;}</style>
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css"/>
    <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css"/>
    
    <meta name="viewport" content="width=device-width,
        initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <style>
        #map_flight_track {
            position: relative;
            width: 100.0%;
            height: 100.0%;
            left: 0.0%;
            top: 0.0%;
        }
        .leaflet-container { font-size: 1rem; }

        .marker-icon {
            /background-color: #fff;
            border: 2px solid #000;
            border-radius: 50%;
            /width: 40px; /* Adjust the width and height as needed */
            /height: 40px; /* Adjust the width and height as needed */
            text-align: center;
            /line-height: 30px;
            font-size: 22px;
            font-weight: bold;
            color: #000;
            /vertical-align: middle;
        }

        .marker-sonde {
            /background-color: #fff;
            background: green;
            border: 2px solid #000;
            border-radius: 50%;
            /width: 40px; /* Adjust the width and height as needed */
            /height: 40px; /* Adjust the width and height as needed */
            text-align: center;
            line-height: 30px;
            font-size: 22px;
            font-weight: bold;
            color: #000;
            /vertical-align: middle;
        }

        .marker-combo-sonde-axbt {
            /width: 30px; /* Adjust width as needed */
            /height: 30px; /* Adjust height as needed */
            background: linear-gradient(to right, green 50%, blue 50%);
            border: 2px solid #000;
            border-radius: 50%; /* Makes the marker round */
            text-align: center;
            line-height: 30px;
            font-size: 22px;
            font-weight: bold;
            color: #000;
        }

        #sidebar {
            position: absolute;
            top: 10px;
            left: 50px;
            width: 200px;
            background-color: #fff;
            padding: 10px;
            border: 1px solid #ccc;
            z-index: 1000; /* Ensure the sidebar appears on top of other elements */
        }

        #sidebar h2 {
            margin-top: 0;
            font-size: 16px;
        }

        #sidebar label {
            display: block;
            margin-bottom: 5px;
        }

        #sidebar input[type="text"],
        #sidebar select {
            width: 100%;
            margin-bottom: 10px;
        }

        #sidebar button {
            width: 100%;
            padding: 8px 0;
            background-color: #007bff;
            color: #fff;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }

        #sidebar button:hover {
            background-color: #0056b3;
        }

    </style>
        
</head>
<body>
    
    
    <div style="position:fixed; bottom:20px; left:220px; z-index:1000;">
        <button id="resetButton">Reset</button>
    </div>
    
    <div id="sidebar">
        <div id="newMarkerSettings">
            <h2>New Marker Settings</h2>
            <label for="markerLat">Latitude:</label>
            <input type="text" id="markerLat" name="markerLat">
            <br>
            <label for="markerLon">Longitude:</label>
            <input type="text" id="markerLon" name="markerLon">
            <br>
            <label for="markerType">Type:</label>
            <select id="markerType" name="markerType">
                <option value="None">None</option>
                <option value="Sonde">Sonde</option>
                <option value="Sonde RMW">Sonde RMW</option>
                <option value="Sonde Mid">Sonde Mid</option>
                <option value="IR Sonde">IR Sonde</option>
                <option value="AXBT">AXBT</option>
                <option value="SUAS">SUAS: Other</option>
                <option value="BlackSwift">SUAS: BlackSwift</option>
                <option value="Altius">SUAS: Altius</option>
                <option value="Buoy">Buoy</option>
                <option value="SailDrone">SailDrone</option>
                <option value="Combo-Sonde-AXBT">Combo (Sonde+AXBT)</option>
                <option value="Combo-Sonde-AXBT-SUAS">Sup Combo (Sonde+AXBT+SUAS)</option>
                <option value="Combo-Sonde-AXBT-IRSonde">Sup Combo (Sonde+AXBT+IRSonde)</option>
                <option value="MPSpiral">Microphys. Spiral</option>
                <option value="Other">Other</option>
            </select>
            <br>
            <label for="markerTurnpoint">Turnpoint:</label>
            <input type="checkbox" id="markerTurnpoint" name="markerTurnpoint">
            <br>
            <button id="applyButton">Insert</button>
        </div>
        <br><br>

        <!-- List of existing markers -->
        <!-- <div id="existingMarkers">
            <h2>Existing Markers</h2>
            <ul id="markerList">
                <!-- Marker list will be populated dynamically here -->
            </ul>
        </div> -->
    </div>
    
    <div class="folium-map" id="map_flight_track" ></div>
        
</body>
<script>

    var map_flight_track = L.map(
        "map_flight_track",
        {"""

    HTML2 = f'{next_line}            center: [{hurrloc[0]}, {hurrloc[1]}],{next_line}'


    HTML3 = """            crs: L.CRS.EPSG3857,
            zoom: 10,
            zoomControl: true,
            preferCanvas: false,
        }
    );

    var tile_layer_flight_track = L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {"attribution": "\\u0026copy; \\u003ca href=\\"https://www.openstreetmap.org/copyright\\"\\u003eOpenStreetMap\\u003c/a\\u003e contributors", "detectRetina": false, "maxNativeZoom": 19, "maxZoom": 19, "minZoom": 0, "noWrap": false, "opacity": 1, "subdomains": "abc", "tms": false}
    );
    tile_layer_flight_track.addTo(map_flight_track);
        
    
    map_flight_track.fitBounds(
"""

    HTML4 = f'        [[{np.min(lats)}, {np.min(lons)}], [{np.max(lats)}, {np.max(lons)}]],{next_line}'

    HTML5 = """        {}
    );

    // Add a marker for the TC center
    var marker_tc_center = L.marker(
"""


    HTML6 = f'        [{hurrloc[0]:.2f}, {hurrloc[1]:.2f}],{next_line}'

    HTML7 = """        {}
    ).addTo(map_flight_track);

    //var icon_tc_center = L.AwesomeMarkers.icon(
    //    {"extraClasses": "fa-rotate-0", "icon": "hurricane", "iconColor": "white", "markerColor": "blue", "prefix": "fa"}
    //);
    var icon_tc_center = L.icon({
        iconUrl: 'https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/icon/hurr_symbol.svg',
        iconSize: [80, 80],
    });
    marker_tc_center.setIcon(icon_tc_center);

    var popup_tc_center = L.popup({"maxWidth": "100%"});

    var html_tc_center = $(`<div id="html_tc_center" style="width: 100.0%; height: 100.0%;"><strong>Storm Center</strong></div>`)[0];
    popup_tc_center.setContent(html_tc_center);

    marker_tc_center.bindPopup(popup_tc_center);
    marker_tc_center.bindTooltip(
        `<div>
             Click for more info
         </div>`,
        {"sticky": true}
    );


    // Create the initial flight track polyline
"""

    HTML8 = '    var poly_line_flight_track = L.polyline('

    for i, (lat, lon) in enumerate(zip(lats, lons)):
       if IS_TURN[i]:
           if i == 0:              HTML8 = HTML8 + f'[[{lat:.2f}, {lon:.2f}], '
           elif i == len(lats)-1:  HTML8 = HTML8 + f'[{lat:.2f}, {lon:.2f}]],{next_line}'
           else:                   HTML8 = HTML8 + f'[{lat:.2f}, {lon:.2f}], '


    HTML9 = """        {
            "bubblingMouseEvents": true,
            "color": "red",
            "dashArray": null,
            "dashOffset": null,
            "fill": false,
            "fillColor": "red",
            "fillOpacity": 0.2,
            "fillRule": "evenodd",
            "lineCap": "round",
            "lineJoin": "round",
            "noClip": false,
            "opacity": 1,
            "smoothFactor": 1.0,
            "stroke": true,
            "weight": 2.5
        }
    )
    .addTo(map_flight_track);

    // Create layerGroups and markers, then add markers to appropriate layerGroup
    var markers_turnpoint = L.layerGroup().addTo(map_flight_track);
    var markers_initial = L.layerGroup();
    var markers_x = L.layerGroup().addTo(map_flight_track);
    var markersx_initial = L.layerGroup();

"""

    HTML10 = ''
    NT, ND = 0, 0
    for j, (lat, lon) in enumerate(zip(lats, lons)):
        i = j+1
        if IS_TURN[j]:
            if IS_DROP[j]:
                HTML10 = HTML10 + f'    var marker_{NT:02d} = createMarker({lat:.2f}, {lon:.2f}, {NT}, "Sonde", true);{next_line}'
            else:
                HTML10 = HTML10 + f'    var marker_{NT:02d} = createMarker({lat:.2f}, {lon:.2f}, {NT}, "None", true);{next_line}'
            HTML10 = HTML10 + f'    marker_{NT:02d}.addTo(markers_turnpoint);{next_line}'
            HTML10 = HTML10 + f'    var marker_{NT:02d}_init = $.extend( true, {sbracket}{ebracket}, marker_{NT:02d} );{next_line}'
            HTML10 = HTML10 + f'    marker_{NT:02d}_init.on({squote}click{squote}, function(){sbracket}{next_line}'
            HTML10 = HTML10 + f'        setMarkerCoordinates(marker_{NT:02d}_init);{next_line}'
            HTML10 = HTML10 + f'    {ebracket});{next_line}'
            HTML10 = HTML10 + f'    marker_{NT:02d}_init.addTo(markers_initial);{next_line}{next_line}'
            NT=NT+1
        elif IS_DROP[j] and not IS_TURN[j]:
            HTML10 = HTML10 + f'    var markerx_{ND:02d} = createMarker({lat:.2f}, {lon:.2f}, {ND}, "Sonde", false);{next_line}'
            HTML10 = HTML10 + f'    markerx_{ND:02d}.addTo(markers_x);{next_line}'
            HTML10 = HTML10 + f'    var markerx_{ND:02d}_init = $.extend( true, {sbracket}{ebracket}, markerx_{ND:02d} );{next_line}'
            HTML10 = HTML10 + f'    markerx_{ND:02d}_init.on({squote}click{squote}, function(){sbracket}{next_line}'
            HTML10 = HTML10 + f'        setMarkerCoordinates(markerx_{ND:02d}_init);{next_line}'
            HTML10 = HTML10 + f'    {ebracket});{next_line}'
            HTML10 = HTML10 + f'    markerx_{ND:02d}_init.addTo(markersx_initial);{next_line}{next_line}'
            ND=ND+1

    HTML11 = """    //// createMarker: Function to create markers, e.g., at flight track turn points
    function createMarker(lat, lon, markerNumber, xType, turnMarker) {
        console.log("createMarker: Create turn-point marker at " + lat + ", " + lon);

        if (turnMarker) {
            var layergroup = markers_turnpoint;
            var markerIcon = chooseTurnMarkerIcon(xType, markerNumber);
        } else {
            var layergroup = markers_x;
            var markerIcon = chooseXMarkerIcon(xType);
        }

        // Create a marker with draggable and other options
        var marker = L.marker([lat, lon], {
            "autoPan": true,
            "draggable": true,
            "icon": markerIcon,
            "color": markerIcon.iconColor,
            id: markerNumber,
            expendable: xType,
            turnMarker: turnMarker
        });
        console.log("createMarker: Marker ID=" + marker.options.id + "; Expendable=" + marker.options.expendable + "; turnMarker=" + turnMarker);

        // Add click event listener for opening coordinate input popup
        marker.on('click', function(){
            setMarkerCoordinates(marker);
        });

        // Add drag event listener for updating polyline on marker drag
        if (turnMarker) {
            // Add double-click event listener for marker removal
            marker.on('dblclick', function(e){
                var index = layergroup.getLayers().indexOf(marker);
                removeMarkerByIndex(layergroup, index);
            });

            marker.on('drag', function(){
                updatePolyline(layergroup, poly_line_flight_track);
            });
        } else {
            marker.on('dblclick', function(e){
                layergroup.removeLayer(marker);
            });
        }

        // Add pop-up open listener to save the current marker
        marker.on('popupopen', function() {
            selectedMarker = marker;
        });

        return marker;
    }


    //// chooseTurnMarkerIcon: function to specify the appropriate marker based on expendable type
    function chooseTurnMarkerIcon(expendableType, index) {
        console.log("chooseTurnMarkerIcon: Choose the appropriate turn-point marker icon");
        // Define marker icon based on expendableType
        var markerIcon;
        switch (expendableType) {
            case "Sonde":
                var markerColor = "green";
                break;
            case "AXBT":
                var markerColor ="blue";
                break;
            case "SUAS":
                var markerColor ="orange";
                break;
            case "IR Sonde":
                var markerColor = "red";
                break;
            case "Combo-Sonde-AXBT":
                var markerColor = "linear-gradient(to right, green 50%, blue 50%)";
                break;
            case "Combo-Sonde-AXBT-SUAS":
                var markerColor = "linear-gradient(to right, green 33%, blue 33%, blue 67%, orange 67%)";
                //var markerColor = "radial-gradient(circle, green 0%, blue 33%, orange 67%)";
                break;
            case "Combo-Sonde-AXBT-IRSonde":
                var markerColor = "linear-gradient(to right, green 33%, blue 33%, blue 67%, red 67%)";
                break;
            case "Other":
                var markerColor = "gray";
                break;
            default:
                // Default color (white) for unknown types
                var markerColor = "white";
                break;
        }

        markerIcon = L.divIcon({
            className: 'turn-marker-icon',
            html: `<div class="marker-icon" style="background: ${markerColor}; line-height: 30px;"> <div class="marker-label">${index}</div> </div>`,
            iconSize: [35, 35],
        });

        return markerIcon;
    }


    //// chooseXMarkerIcon: function to specify the appropriate marker based on expendable type
    function chooseXMarkerIcon(expendableType) {
        console.log("chooseXMarkerIcon: Choose the appropriate expendable marker icon");
        // Define marker icon based on expendableType
        var markerIcon;
        switch (expendableType) {
            case "Sonde":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: green; line-height: 25px;"> <div class="marker-label">S</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "Sonde RMW":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: green; line-height: 25px;"> <div class="marker-label">R</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "Sonde Mid":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: green; line-height: 25px;"> <div class="marker-label">M</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "IR Sonde":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: red; line-height: 25px;"> <div class="marker-label">I</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "AXBT":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: blue; line-height: 25px;"> <div class="marker-label">A</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "Buoy":
                markerIcon = L.icon({
                    iconUrl: 'https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/icon/buoy-simple.svg',
                    iconSize: [40, 40],
                });
                break;
            case "SailDrone":
                markerIcon = L.icon({
                    iconUrl: 'https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/icon/saildrone-simple.svg',
                    iconSize: [50, 50],
                });
                break;
            case "SUAS":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: orange; line-height: 25px;"> <div class="marker-label">U</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "BlackSwift":
                markerIcon = L.icon({
                    iconUrl: 'https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/icon/blackswift-s0-marker-v2.svg',
                    iconSize: [40, 40],
                });
                break;
            case "Altius":
                markerIcon = L.icon({
                    iconUrl: 'https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/icon/anduril-altius600-marker.svg',
                    iconSize: [40, 40],
                });
                break;
            case "Combo-Sonde-AXBT":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: linear-gradient(to right, green 50%, blue 50%); line-height: 25px;"> <div class="marker-label">C</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "Combo-Sonde-AXBT-SUAS":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: linear-gradient(to right, green 33%, blue 33%, blue 67%, orange 67%); line-height: 25px;"> <div class="marker-label">SC</div> </div>`,
                    iconSize: [40, 40],
                });
                break;
            case "Combo-Sonde-AXBT-IRSonde":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: linear-gradient(to right, green 33%, blue 33%, blue 67%, red 67%); line-height: 25px;"> <div class="marker-label">SC</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            case "MPSpiral":
                markerIcon = L.icon({
                    iconUrl: 'https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/icon/spiral.png',
                    iconSize: [30, 30],
                });
                break;
            case "Other":
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: gray; line-height: 25px;"> <div class="marker-label">O</div> </div>`,
                    iconSize: [30, 30],
                });
                break;
            default:
                // Default color (white) for unknown types
                markerIcon = L.divIcon({
                    className: 'x-marker-icon',
                    html: `<div class="marker-icon" style="background: white; line-height: 25px;"> <div class="marker-label">N</div> </div>`,
                    iconSize: [30, 30],
                });
                break;

        }
        return markerIcon;
    }


    //// updatePolyline: function that updates the flight track polyline
    function updatePolyline(markers, polyline) {
        console.log("updatePolyline: Update flight-track polyline");
        var latlngs = [];
        markers.eachLayer(function(marker) {
            latlngs.push(marker.getLatLng());
        });
        polyline.setLatLngs(latlngs);
        var latlngs = polyline.getLatLngs();
    }

    // Update the polyline based on the markers
    updatePolyline(markers_turnpoint, poly_line_flight_track);

    // Whenever markers are added/removed/updated, call `updatePolyline` again
    markers_turnpoint.on('layeradd layerremove', function() {
        updatePolyline(markers_turnpoint, poly_line_flight_track);
        updateMarkerNumbers(markers_turnpoint); // Update marker numbers after layerGroup is modified
    });


    //// onMapClick: Add a point to a polyline when it is clicked
    function onMapClick(e, polyline, layergroup, map) {
        console.log("onMapClick: Actions to take after the map is clicked");
        // Get the clicked coordinates
        var clickedLatLng = e.latlng;
        var new_marker = createMarker(clickedLatLng.lat, clickedLatLng.lng, layergroup.getLayers().length + 1, "Sonde", false);
        layergroup.addLayer(new_marker);
        // update the flight track
        //updatePolyline(layergroup,polyline);
        //console.log("onMapClick: Expendable Type Array 2: " + xtype_turnpoint);
        //updateMarkerNumbers(layergroup); // Update marker numbers after marker created on click
        //updateSidebarMarkerList(layergroup);
    };

    // Attach the click event listener to the map
    map_flight_track.on('click', function(e){
        //console.log("Map click event: " + xtype_turnpoint);
        onMapClick(e, poly_line_flight_track, markers_x, map_flight_track);
    });


    //// Function to manually set the lat/lon for each marker
    function setMarkerCoordinates(marker) {
        console.log("setMarkerCoordinates: Setting marker pop-up coordinates");
        var expendableType = marker.options.expendable;
        var expendableLongName = getExpendableLongName(expendableType);
        var popupContent = `
            <div>
                <h2>${expendableLongName}</h2>
                <p>Enter lat/lon:</p>
                <input type="text" id="marker-lat" value="${marker.getLatLng().lat}">
                <input type="text" id="marker-lng" value="${marker.getLatLng().lng}">
                Expendable/Module:
                <select id="marker-expendable">
                    <option value="None" ${expendableType === 'None' ? 'selected' : ''}>None</option>
                    <option value="Sonde" ${expendableType === 'Sonde' ? 'selected' : ''}>Sonde</option>
                    <option value="Sonde RMW" ${expendableType === 'Sonde RMW' ? 'selected' : ''}>Sonde RMW</option>
                    <option value="Sonde Mid" ${expendableType === 'Sonde Mid' ? 'selected' : ''}>Sonde Mid</option>
                    <option value="IR Sonde" ${expendableType === 'IR Sonde' ? 'selected' : ''}>IR Sonde</option>
                    <option value="AXBT" ${expendableType === 'AXBT' ? 'selected' : ''}>AXBT</option>
                    <option value="Buoy" ${expendableType === 'Buoy' ? 'selected' : ''}>Buoy</option>
                    <option value="SailDrone" ${expendableType === 'SailDrone' ? 'selected' : ''}>SailDrone</option>
                    <option value="SUAS" ${expendableType === 'SUAS' ? 'selected' : ''}>SUAS: Other</option>
                    <option value="BlackSwift" ${expendableType === 'BlackSwift' ? 'selected' : ''}>SUAS: BlackSwift</option>
                    <option value="Altius" ${expendableType === 'Altius' ? 'selected' : ''}>SUAS: Altius</option>
                    <option value="Combo-Sonde-AXBT" ${expendableType === 'Combo-Sonde-AXBT' ? 'selected' : ''}>Combo (Sonde+AXBT)</option>
                    <option value="Combo-Sonde-AXBT-SUAS" ${expendableType === 'Combo-Sonde-AXBT-SUAS' ? 'selected' : ''}>Sup. Combo (Sonde+AXBT+SUAS)</option>
                    <option value="Combo-Sonde-AXBT-IRSonde" ${expendableType === 'Combo-Sonde-AXBT-IRSonde' ? 'selected' : ''}>Sup. Combo (Sonde+AXBT+IRSonde)</option>
                    <option value="MPSpiral" ${expendableType === 'MPSpiral' ? 'selected' : ''}>Microphys. Spiral</option>
                    <option value="Other" ${expendableType === 'Other' ? 'selected' : ''}>Other</option>
                </select>
                <button onclick="applyChanges()">Apply</button>
            </div>`;
        marker.bindPopup(popupContent).openPopup();
    }

    //// Function to apply changes to marker location and expendable type
    function applyChanges() {
        // Use the selectedMarker variable to access the marker object
        var marker = selectedMarker;

        var lat = parseFloat(document.getElementById('marker-lat').value);
        var lng = parseFloat(document.getElementById('marker-lng').value);
        var xType = document.getElementById('marker-expendable').value;
        console.log("applyChanges: lat,lon,xType = " + lat + lng + xType)
            
        // Update marker location
        var newLatLng = L.latLng(lat, lng);
        marker.setLatLng(newLatLng);

        // Update expendable type in marker options
        marker.options.expendable = xType;

        if (marker.options.turnMarker) {
            // Update marker icon based on the new expendable type
            var markerIcon = chooseTurnMarkerIcon(xType, marker.options.id);
            marker.setIcon(markerIcon);

            updatePolyline(markers_turnpoint, poly_line_flight_track);
            updateMarkerNumbers(markers_turnpoint); // Update marker numbers after removal
            //updateSidebarMarkerList(markers_turnpoint);
        } else {
            // Update marker icon based on the new expendable type
            var markerIcon = chooseXMarkerIcon(xType);
            marker.setIcon(markerIcon);
        }

        // Add click event listener for opening coordinate input popup
        marker.on('click', function(){
            setMarkerCoordinates(marker);
        });

        marker.closePopup();
    }


    //// getExpendableLongName
    function getExpendableLongName(xType) {
        switch (xType) {
            case "Sonde":
                longName = "Dropsonde";
                break;
            case "Sonde RMW":
                longName = "RMW Dropsonde";
                break;
            case "Sonde Mid":
                longName = "Midpoint Dropsonde";
                break;
            case "IR Sonde":
                longName = "IR Dropsonde";
                break;
            case "AXBT":
                longName = "Airborne EXpendable BathyThermograph";
                break;
            case "Buoy":
                longName = "Buoy";
                break;
            case "SailDrone":
                longName = "SailDrone";
                break;
            case "SUAS":
                longName = "Small Uncrewed Aircraft System";
                break;
            case "BlackSwift":
                longName = "BlackSwift S0 SUAS";
                break;
            case "Altius":
                longName = "Anduril Altius SUAS";
                break;
            case "Combo-Sonde-AXBT":
                longName = "Combo (Sonde+AXBT)";
                break;
            case "Combo-Sonde-AXBT-SUAS":
                longName = "Super Combo (Sonde+AXBT+SUAS)";
                break;
            case "Combo-Sonde-AXBT-IRSonde":
                longName = "Super Combo (Sonde+AXBT+IRSonde)";
                break;
            case "MPSpiral":
                longName = "HFP Module: Microphysics Spiral";
                break;
            case "Other":
                longName = "Other (Unknown)";
                break;
            default:
                longName = "No Expendable";
                break;

        }
        return longName;
    }


    //// updateMarkerNumbers: Function to update marker numbers
    function updateMarkerNumbers(layergroup) {
        console.log("updateMarkerNumbers: Update the turn-point marker numbers");
        var markers = layergroup.getLayers();
        layergroup.clearLayers();
        markers.forEach(function(marker, index) {
            //console.log("Expendable Type update: " + xtypes[index]);
            var latlng = marker.getLatLng();
            var markerWithIcon = createMarker(latlng.lat, latlng.lng, index + 1, marker.options.expendable, true); // Create marker with custom icon
            layergroup.addLayer(markerWithIcon);
        });
    }


    //// removeMarkerByIndex: Function to remove a marker by its index
    function removeMarkerByIndex(layergroup, index) {
        console.log("removeMarkerByIndex: Remove turn-point markers anywhere on the polyline");
        var markers = layergroup.getLayers();
        if (index >= 0 && index < markers.length) {
            var removedMarker = markers[index];
            map_flight_track.removeLayer(removedMarker);
            layergroup.removeLayer(removedMarker);
            updatePolyline(layergroup, poly_line_flight_track);
            updateMarkerNumbers(layergroup); // Update marker numbers after removal
            //updateSidebarMarkerList(layergroup);
        }
    }

    // get a reference to the reset button
    var resetButton = document.getElementById('resetButton');
    // attach a click event listener to the reset button
    resetButton.addEventListener('click', function() {
        // Clear all markers from the map
        map_flight_track.removeLayer(markers_turnpoint);
        markers_turnpoint.clearLayers();
        markers_x.clearLayers();
        // Add the initial markers back to the markers_turnpoint layer group
        markers_initial.eachLayer(function(marker) {
            var new_marker = createMarker(marker.getLatLng().lat, marker.getLatLng().lng, markers_turnpoint.getLayers().length + 1, "None", true);
            markers_turnpoint.addLayer(new_marker);
        });
        markers_turnpoint.addTo(map_flight_track);
        markersx_initial.eachLayer(function(marker) {
            var new_marker = createMarker(marker.getLatLng().lat, marker.getLatLng().lng, markers_x.getLayers().length + 1, "Sonde", false);
            markers_x.addLayer(new_marker);
        });
        markers_x.addTo(map_flight_track);
        updatePolyline(markers_turnpoint,poly_line_flight_track);
        //updateSidebarMarkerList(markers_turnpoint);
    });

    // Function to update the sidebar with marker information
    function updateSidebarMarkerList(markers) {
        console.log("updateSidebarMarkerList: update the sidebar marker list");
        // Clear existing marker list
        var markerList = document.getElementById("markerList");
        markerList.innerHTML = ""; // Clear the existing list
          
        // Iterate through each marker and add it to the sidebar
        markers.eachLayer(function(marker, index) {
            var markerItem = document.createElement("li");
            console.log("updateSidebarMarkerList: Marker ID=" + marker.options.id + "; Expendable=" + marker.options.expendable);
            // Create a dropdown menu for expendable type selection
            var expendableSelect = document.createElement("select");
            expendableSelect.addEventListener("change", function() {
                updateExpendableType(marker, this.value); // Update the expendable type for the marker
            });
                    
            // Add options to the dropdown menu
            var expendableTypes = ["None", "Sonde", "Sonde RMW", "Sonde Mid", "AXBT", "SUAS", "IR Sonde", "Buoy", "SailDrone", "Combo-Sonde-AXBT", "Combo-Sonde-AXBT-SUAS", "Combo-Sonde-AXBT-IRSonde", "Other"];
            expendableTypes.forEach(function(type) {
                var option = document.createElement("option");
                option.value = type;
                option.text = type;
                expendableSelect.appendChild(option);
            });
                    
            // Set the selected option based on the marker's current expendable type
            expendableSelect.value = marker.options.expendable; 
 
            markerItem.textContent = "Marker " + marker.options.id + ": " + marker.getLatLng().toString(); // Display marker coordinates
            markerItem.appendChild(expendableSelect);
            markerList.appendChild(markerItem);
        });
    }    
        
    // Call the updateSidebar function initially to populate the sidebar with existing markers
    //updateSidebarMarkerList(markers_turnpoint);
            
    // Whenever markers are added/removed/updated, call updateSidebar to reflect the changes in the sidebar
    //markers_turnpoint.on('layeradd layerremove', function() {
    //    updateSidebarMarkerList(markers_turnpoint);
    //});


    document.getElementById("applyButton").addEventListener("click", function() {
        var markerLat = document.getElementById("markerLat").value;
        var markerLon = document.getElementById("markerLon").value;
        var markerType = document.getElementById("markerType").value;
        var markerTurnpoint = document.getElementById("markerTurnpoint").checked;
        console.log("markerTurnpoint=" + markerTurnpoint);

        // Check if latitude and longitude are provided
        if (markerLat !== "" && markerLon !== "") {
            // Place marker at the specified location
            var latlng = L.latLng(parseFloat(markerLat), parseFloat(markerLon));
                     
            if (markerTurnpoint) {
                var new_marker = createMarker(latlng.lat, latlng.lng, markers_turnpoint.getLayers().length + 1, markerType, markerTurnpoint);
                markers_turnpoint.addLayer(new_marker);
                updatePolyline(markers_turnpoint, poly_line_flight_track);
                updateMarkerNumbers(markers_turnpoint);
            } else {
                var new_marker = createMarker(latlng.lat, latlng.lng, markers_x.getLayers().length + 1, markerType, markerTurnpoint);
                markers_x.addLayer(new_marker);
                //updateMarkerNumbers(markers_x);
            }
         }
     });


    //// Function to update the expendable type for a marker
    function updateExpendableType(marker, newType) {
        console.log("updateExpendableType: update the expendable type for a marker");
        var markerIndex = marker.options.id;
        marker.options.expendable = newType;
        console.log("updateExpendableType: Marker ID=" + markerIndex + "; Expendable=" + newType);
        if (markerIndex !== -1 && markerIndex <= markers_turnpoint.getLayers().length) {
            // Update the marker icon to match the new expendable type
            var markerIcon = chooseTurnMarkerIcon(newType, markerIndex + 1); // Assuming markerIndex starts from 1
            marker.setIcon(markerIcon);
            updateMarkerNumbers(markers_turnpoint);
            //updateSidebarMarkerList(markers_turnpoint); // Update the marker list to reflect the changes
        }
    }

       
</script>
</html>
"""

    HTML_FILE.write(HTML1)
    HTML_FILE.write(HTML2)
    HTML_FILE.write(HTML3)
    HTML_FILE.write(HTML4)
    HTML_FILE.write(HTML5)
    HTML_FILE.write(HTML6)
    HTML_FILE.write(HTML7)
    HTML_FILE.write(HTML8)
    HTML_FILE.write(HTML9)
    HTML_FILE.write(HTML10)
    HTML_FILE.write(HTML11)
    HTML_FILE.close()

    print(f'MSG: Created output: tkmap{N}.html')

    print(f'MSG: Module WRITE_HTML completed at {datetime.datetime.now()}')



###########################################################
###########################################################
def CITY_LOCATION(CITY, FNAME='citylocs'):
    """Retreive city/station/base location (lat, lon).

    @param CITY (string):  city name
    @kwarg FNAME (string): file name containing city coordinates

    @return (float): tuple(latitude, longitude)
    """
    lat, lon = None, None
    with open(FNAME, 'r') as f:
        for line in f:
            if CITY in line:
                line = line.replace(CITY, ' ')
                lat, lon = np.float128(line.split()[0].strip()), np.float128(line.split()[1].strip())
    return lat, lon



###########################################################
###########################################################
def AIRCRAFT_DFLT(iac):
    """Aircraft defaults.

    @param iac (integer): aircraft number

    @return: tuple(speed (float), low altitude (integer),
                   high altitude (integer),
                   non drops to turns (boolean))
    """
    # NOAA WP-3D
    if int(iac) in [42, 43]:
        speed, ialt1, ialt2, globalhawk = 330., 0, 10, True
    # NOAA G-IV
    elif int(iac) == 49:
        speed, ialt1, ialt2, globalhawk = 442., 41, 45, True
    # AF C130-J
    elif int(iac) == 50:
        speed, ialt1, ialt2, globalhawk = 290., 18, 38, True
    # NASA DC-8
    elif int(iac) == 51:
        speed, ialt1, ialt2, globalhawk = 440., 18, 38, True
    # Global Hawk
    elif int(iac) == 52:
        speed, ialt1, ialt2, globalhawk = 335., 55, 60, True
    # AF WB-57
    elif int(iac) == 57:
        speed, ialt1, ialt2, globalhawk = 300., 40, 60, True

    return np.float128(speed), ialt1, ialt2, globalhawk


###########################################################
###########################################################
def DGMN(ddeg):
    """Convert from decimal degrees/hours to degrees/hours + minutes

    @param ddeg (float): Decimal degrees/hours

    @return (integer): tuple(degrees/hours, minutes)
    """
    #ideg = abs(int(ddeg))
    #min_ = round((abs(np.float128(ddeg)) - np.float128(ideg)) * np.float128(60.))
    ideg = int(abs(np.round(ddeg)))
    min_ = int(np.round((abs(ddeg) - np.float128(ideg)) * 60.))
    
    if min_ >= 60:
        min_ = min_ - 60
        ideg += 1
    elif min_ < 0:
        min_ = 60 + min_
        ideg -= 1
    
    if ddeg < 0:
        ideg = -ideg
    
    return ideg, min_


###########################################################
###########################################################
def GCDISTANCE(YY, XX, BB, AA, units='NM'):
    """Calculate the great circle distance between two points
on the Earth's surface using angular separation.

    @param YY    (float):  first latitude in degrees
    @param XX    (float):  first longitude in degrees
    @param BB    (float):  second latitude in degrees
    @param AA    (float):  second longitude in degrees
    @kwarg units (string): output units

    @return (float): great circle distance
    """
    # Define Earth's radius in requested units
    if units in ['NM', 'km']:
        if units == 'km':
            REARTH = np.float128(6378.163)
        elif units == 'NM':
            REARTH = np.float128(6378.163) * np.float128(60.) / np.float128(111.12)
    else:
        print(f'Error: {units} is not a recognized unit. Please choose NM or km.')
        sys.exit(1)

    # Check if the two locations (XX, YY) & (AA, BB) are identical
    if YY == BB and XX == AA:
        return np.float128(0.0)

    # Convert to radians
    Y = np.radians(np.float128(YY))
    X = np.radians(np.float128(XX))
    A = np.radians(np.float128(AA))
    B = np.radians(np.float128(BB))

    # Calculate the angular separation betwen the two points
    #ANGLE = np.arccos(np.cos(A - X) * np.cos(Y) * np.cos(B) + np.sin(Y) * np.sin(B))
    ANGLE = np.arccos(np.sin(Y) * np.sin(B) + np.cos(Y) * np.cos(B) * np.cos(X - A))

    return ANGLE * REARTH


def GCDISTANCE2(lat1, lon1, lat2, lon2, nmi_flag=True):
    """Calculate the great circle distance between two points
on the Earth's surface using the Haversine formula.

    @param lat1 (float):       Latitude 1 in degrees
    @param lon1 (float):       Longitude 1 in degrees
    @param lat2 (float):       Latitude 2 in degrees
    @param lon2 (float):       Longitude 2 in degrees
    @kwarg nmi_flag (boolean): Convert to nautical miles

    @return (float): The distance between the two points (in kilometers or nautical miles)
    """
    # Convert latitude and longitude from degrees to radians
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.atan2(np.sqrt(a), np.sqrt(1 - a))

    # Radius of the Earth in kilometers
    R = 6371.0

    # Calculate the distance
    distance = R * c

    if nmi_flag:
        distance = np.float128(0.539957)*distance

    return distance



###########################################################
###########################################################
def GETSPEED(iac, alt):
    """Calculate the speed of certain aircraft under different conditions
e.g., different altitudes.

    @param iac (integer): aircaft number
    @param alt (float):   altitude (in kft)

    @return (float): calibrated speed
    """
    if iac in [42, 43]:
        if alt >= 5000. and alt <= 8000.:
          speedcal = np.float128(218.) + (np.float128(232.) - np.float128(218.)) * (np.float128(alt) - np.float128(5000.)) / np.float128(3000.)
        elif alt > 8000. and alt <= 10000.:
          speedcal = np.float128(232.) + (np.float128(242.) - np.float128(232.)) * (np.float128(alt) - np.float128(8000.)) / np.float128(2000.)
        elif alt > 10000. and alt <= 12000.:
          speedcal = np.float128(242.) + (np.float128(252.) - np.float128(242.)) * (np.float128(alt) - np.float128(10000.)) / np.float128(2000.)
        elif alt > 12000. and alt <= 20000.:
          speedcal = np.float128(252.) + (np.float128(300.) - np.float128(252.)) * (np.float128(alt) - np.float128(12000.)) / np.float128(8000.)
        else:
          speedcal = np.float128(300.)
    elif iac == 57:
        if alt >= 60000.:
          speedcal = np.float128(400.)
        elif alt <= 40000:
          speedcal = np.float128(300.)
        else:
          speedcal = np.float128(300.) + np.float128(100.) * (np.float128(alt) - np.float128(30000.)) / np.float128(10000.)

    return speedcal


###########################################################
###########################################################
def KM_PER_DEGREE(latitude):
    """Calculate kilometers per degree latitude and longitude
accounting for Earth's oblate shape and variation in
circumference at difference latitudes.

    @param latitude (float):  Latitude in decimal degrees

    @return: tuple(km per degree latitude, km per degree longitude)
    """
    lat_rad = np.radians(np.float128(latitude))

    km_per_lat = 111.13209 - 0.56605 * np.cos(2.0 * lat_rad) + \
        0.00012 * np.cos(4.0 * lat_rad) - \
        0.000002 * np.cos(6.0 * lat_rad)

    km_per_lon = 111.41513 * np.cos(lat_rad) - \
        0.09455 * np.cos(3.0 * lat_rad) + \
        0.00012 * np.cos(5.0 * lat_rad)

    return km_per_lat, km_per_lon


def KM_PER_DEGREE2(latitude):
    """Calculate kilometers per degree latitude and longitude
given a specific latitude using WGS 84 ellipsoid model.
    
    @param latitude (float):  Latitude in decimal degrees
    
    @return (float): tuple(km per degree latitude, km per degree longitude)
    """
    # Constants for WGS 84 ellipsoid model
    a = np.float128(6378.137)        # equatorial radius in kilometers
    b = np.float128(6356.752313245)  # polar radius in kilometers

    # Convert latitude to radians
    lat_rad = np.radians(np.float128(latitude))

    # Radius of curvature in the prime vertical
    N = a**2 / np.sqrt(a**2 * np.cos(lat_rad)**2 + b**2 * np.sin(lat_rad)**2)
    #M = (a * (1 - (a - b) / a)**2) / np.sqrt((a * np.cos(lat_rad))**2 + (b * np.sin(lat_rad))**2)

    # Calculate kilometers per degree latitude and longitude
    km_per_lat = np.radians(np.float128(1.)) * np.float128(N)
    km_per_lon = np.radians(np.float128(1.)) * np.float128(N) * np.cos(lat_rad)

    return km_per_lat, km_per_lon



###########################################################
###########################################################
def SRLATLON(SLAT, SLON, THETA, R):
    """Compute storm-relative latitude & longitude points.

    @param SLAT  (float):  Storm center latitude
    @param SLON  (float):  Storm center longitude
    @param THETA (float):  Azimuthal angle relative to true North
    @param R     (float):  Radial distance from the storm center

    @return (float): tuple(latitude, longitude)
    """
    NM2km = np.float128(111.12)/np.float128(60.)

    DX = np.float128(R) * np.sin(np.radians(np.float128(THETA)))
    DY = np.float128(R) * np.cos(np.radians(np.float128(THETA)))

    KMDEGLAT, KMDEGLON = KM_PER_DEGREE(SLAT)
    YLAT = np.float128(SLAT) + DY / KMDEGLAT
    YLON = np.float128(SLON) + DX / KMDEGLON
    #print(f'TH={THETA}, R={R}, DX={DX}, DY={DY}')
    #print(f'KMDEGLAT={KMDEGLAT}, KMDEGLON={KMDEGLON}')
    #print(f'SLAT={SLAT}, SLON={SLON}, YLAT={YLAT}, YLON={YLON}')

    # Scale the distance to ensure that this point (YLAT,YLON)
    # is exactly R km away from the storm center (SLAT,SLON)
    DIST = NM2km * GCDISTANCE(SLAT, SLON, YLAT, YLON)
    if DIST == 0.0:
        return YLAT, YLON
    SCALE = R / DIST
    DX = DX * SCALE
    DY = DY * SCALE
    YLAT = np.float128(SLAT) + DY / KMDEGLAT
    YLON = np.float128(SLON) + DX / KMDEGLON

    return YLAT, YLON



###########################################################
###########################################################
def UVCOMP(heading, spd):
    """Compute the zonal (C) and meridional (V) components based on
heading and speed.

    @param heading (float): Heading angle relative to true North
    @param spd     (float): Vector magnitude (e.g., storm speed)

    @return (float): tuple(u-component, v-component)
    """
    new_hdg = 90. - np.float128(heading)
    if new_hdg < 0.:  new_hdg = new_hdg + 360.
    u, v = np.float128(spd) * np.cos(np.radians(new_hdg)), np.float128(spd) * np.sin(np.radians(new_hdg))
    return u, v


###########################################################
###########################################################
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="TKMAP options")
    parser.add_argument("--maxtrax", type=int, default=4, help="Max number of flight tracks")
    parser.add_argument("--no_plot", action="store_false", help="Disable plotting")
    parser.add_argument("--no_html", action="store_false", help="Disable HTML generation")
    parser.add_argument("--east_hemisphere", action="store_false", help="Force eastern hemisphere (WestHS=False)")
    parser.add_argument("--no_storm_center_update", action="store_false", help="Do not update the storm center position")
    parser.add_argument("--no_stormrel_latlon_update", action="store_false", help="Do not update storm-relative lat/lon aircraft positions")
    parser.add_argument("--verbose", type=int, default=1, help="Verbose level (0=none, 1=some, 2=most, 3=all)")

    args = parser.parse_args()

    if args.verbose < 0 or args.verbose > 3:
        print('ERROR: Unrecognized verbosity level {args.verbose}')
        print('ERROR: Please choose an integer verbosity level 0-3')
        sys.exit(1)

    TKMAP(MAXTRAX=args.maxtrax, DO_PLOT=args.no_plot, DO_HTML=args.no_html, WestHS=args.east_hemisphere, UPDATE_STM_CENTER=args.no_storm_center_update, UPDATE_SRLATLON=args.no_stormrel_latlon_update, verbose=args.verbose)

