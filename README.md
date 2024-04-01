# TKMAP README

## DESCRIPTION

TKMAP is HRD's flight track software that has been used to prepare aicraft reconnassaince missions,
including for NOAA's Hurricane Field Program, for several decades. The first documented version of
TKMAP was written by James Franklin (HRD) in Jul/1986, with subsequent updates in Feb/1989, and
Feb/1996. The initial purpose of this software was to provide flight tracks for NOAA G-IV missions.
Sim Aberson (HRD) added capabilities to produce flight tracks for NOAA WP-3D aircraft, specifically
N42 and N43. Other aicraft were eventually added later on. Paul Leighton (HRD) and Jason Dunion
(HRD) also made important modifications, specifically to account for GlobalHawk requiremenets.
Ghassan Alaka (HRD) converted the software from FORTRAN to Python in Mar/2024.

TKMAP creates a full flight plan, including turn points, expendable (dropsonde) points,
flight time, total distbance, etc., for a variety of NOAA/AF/NASA aircraft. This version relies
solely on Python to calculate the flight track and visualize it.

TKMAP consists of three modules:
1. **TRACKDIS**:     Calculate the flight track distance and time (always turned on)
2. **MAKE_GRAPHIC**: Create a static PNG image of one or more flight tracks (optional, '--no_plot' command-line arg turns it off, see below)
3. **WRITE_HTML**:   Create an HTML file to visualize and modify each flight track (optional, '--no_html' command-line arg turns it off, see below)

Supported aicraft include:
- **42 (NOAA P-3)**:    FL=5000ft (218kt); FL=6000ft (223kt); FL=7000ft (227kt); FL=8000ft (232kt); FL=9000ft (237kt); FL=10000ft (242kt); FL=11000ft (247kt); FL=12000ft (252kt); FL=14000ft (264kt); FL=18000ft (288kt); FL>=20000ft (300kt)
- **43 (NOAA P-3)**:    same as NOAA 42
- **49 (NOAA G-IV)**:   FL=41000-45000ft (442kt)
- **50 (AF C-130J)**:   FL=18000-25000ft (290kt)
- **51 (NASA DC-8)**:   FL:18000-25000ft (350kt)
- **52 (GLOBAL HAWK)**: FL=55000-60000ft (335kt)
- **57 (NASA WB-57)**:  FL>=60000ft (400kt); FL=55000ft (550kt); FL=50000ft (500kt); FL=45000ft (450kt); FL<=40000ft (300kt)

Known modifications:
- 1986/07:    Original version (J. Franklin)
- 1989/02:    Modifications to TRACKDIS (J. Franklin)
- 1996/02:    Further TRACKDIS mods (J. Franklin)
- 2017/05/22: Updated to include Lakeland
- 2017/05/22: Updated to keep graphics alive during run
- 2024/04/01: Updated to 100% Python, including flight track calculation and text/graphical/html products (G. Alaka)



## INSTALLATION

To install the necessary components required for TKMAP:

1. Python (>= 3.12) must be installed. If you need to install it, Miniconda is recommended (https://docs.anaconda.com/free/miniconda/miniconda-install/).
2. Python must include the following packages: numpy, matploblib, & cartopy. To install these packages yourself, follow these steps:
   - Create/load a conda environment of your choosing. For help, please refer to [Conda documentation](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).
   - Install numpy >= 1.26.4 (e.g., execute `conda install numpy`)
   - Install matplotlib >= 3.8.0 (e.g., execute `conda install matplotlib`)
   - Install cartopy >= 0.22.0 (e.g., execute `conda install cartopy`)
3. Alternatively, you can download, unzip, and source the following pre-packaged conda environment. Note that Python must already be installed).
   - Download [TKMAP Python environment](https://www.aoml.noaa.gov/ftp/hrd/ghassan.alaka/tkmap/tkmap_environment.tar.gz).
   - Unzip the file (e.g., execute `tar -xzf tkmap_environment.tar.gz`).
   - Source the file (e.g., execute `source ./bin/activate`).



## EXECUTION

To run TKMAP:

1. Navigate to your TKMAP directory.

2. The input file(s) are 'current[1-4].ftk' and must be located in the TKMAP directory. At the very least, 'current1.ftk' must be available. Additional input files ('current[2-4].ftk') can be used if multiple aircraft are deployed. 'current1.ftk' file structure:
   - Line 1
     - Specify the aircraft number and takeoff time (dd/hhmmZ).
     - You may optionally include a title (like the storm or experiment name).
     - Example: `42 23/2200Z Genesis`

   - Lines 2+: First character indicates what type of data follows:
     - "**H**"
       - Location of the storm or target and its expected motion vector.
       - Optional, but must be the second line if included.
       - Example: `H 18.5 82.5 270 15`
     - "**A**"
       - Takeoff location (city/station/base).
       - Example: `A MACDILL`
     - "**S**"
       - Storm-relative radius (NM) and azimuth (deg from N), plus altitude (ft).
       - "H" line must be already defined.
       - Example: `S 180 330 5000`
     - "**blank**"
       - Earth-relative latitude (deg), longitude (deg), and altitude (ft).
       - Example: `  24 83.5 20000`
     - "**I**"
       - Number and altitude (ft) of intermediate drop points between turn points.
       - Example: `I 4 10000`
     - "**T**"
       - Earth-relative turn point without a drop.
       - Example: `T 24 83.5 20000`
     - "**Z**"
       - Landing location (city/station/base).
       - Example: `Z MACDILL`
   - See examples of `current1.ftk` below.

3. Execute the following command:
   ```bash
   python tkmap.py [-h] [--maxtrax MAXTRAX] [--no_plot] [--no_html] [--east_hemisphere] [--no_storm_center_update] [--no_stormrel_latlon_update] [--verbose VERBOSE]

   - Options:
     - `-h`, `--help`: Show help message
     - `--maxtrax MAXTRAX`: Max number of flight tracks
     - `--no_plot`: Disable plotting
     - `--no_html`: Disable HTML generation
     - `--east_hemisphere`: Force eastern hemisphere (WestHS=False)
     - `--no_storm_center_update`: Do not update the storm center position
     - `--no_stormrel_latlon_update`: Do not update storm-relative lat/lon aircraft positions
     - `--verbose VERBOSE`: Verbose level (0=none, 1=some, 2=most, 3=all)

4. Additional notes
   - For faster execution, try: `python -B tkmap.py [...]`
   - For faster execution, try: `python -m compileall tkmap.py`



## Output

Up to 7 output files could be created. `TRACKDIS` creates 5 output text files. `MAKE_GRAPHIC` produces 1 PNG file. `WRITE_HTML` produces 1 HTML file.

- **module TRACKDIS:**
  - `turns[NF].txt`: Formatted ASCII text with all turn points
  - `drops[NF].txt`: Formatted ASCII text with all drop points
  - `points[NF]`: Lat/lon for all points
  - `points_extra[NF]`: Lat/lon plus drop/turn info (1-True, 0-False) for all points
  - `hurrloc[NF]`: TC location

- **module MAKE_GRAPHIC:**
  - `tkmap1.png`: Static image of 1+ flight tracks

- **module WRITE_HTML:**
  - `tkmap1.html`: HTML file to visualize and modify all points

Check to make sure that the flight duration is within the limits (below) and that the graphics look fine.

### Maximum P-3 Flight Durations (determined by landing site):
- Bermuda: 8.0 hr (~2150 nm)
- Barbados/St. Croix: 9.0 hr (~2400 nm)
- Mainland: 9.0 hr (~2400 nm)
- P-3 2015 engine upgrade allows for up to 11.0 hr (~2900 nm)
  - 11.0 hr flight consideration: slips in take-off time will result in the following day (crew rest requirements)

### Maximum G-IV Flight Durations (determined by landing site):
- Bermuda: 7.5 hr (~3300 nm)
- Barbados/St. Croix: 8.0 hr (~3500 nm)
- Mainland: 8.5 hr (~3750 nm)

### Maximum Global Hawk Flight Duration
- All deployment sites: ~24.0 hr (~8,000 nm)
  - 24.0 hr includes ~30 min for the initial climb out plus ~30 in for the final decent out of/back to NASA Armstrong/Wallops.
  - `tkmap` automatically adds 30-min & 167.5 nm to the track after take-off and after the last way point to account for these aircraft maneuvers



## EXAMPLES

### EXAMPLE 1

- **current1.ftk**:
```
42 23/2200Z
H 25.0 83.2 000 00
A MACDILL
S 105 0 12000
S 105 180 12000
S 105 135 12000
S 105 315 12000
S 105 270 12000
S 105 90 12000
S 105 45 12000
S 105 225 12000
S 105 180 12000
S 105 0 12000
Z MACDILL
```

- **turns1.txt**:
```
 ========================================================================
 MISSION PLAN:  Unknown

 Prepared by the Hurricane Research Division File: current1.ftk

 Aircraft: N42RF  Proposed takeoff: 23/2200Z
 ========================================================================


 TRACK DISTANCE TABLE

 ===========================================================
  #      LAT      LON     RAD/AZM     LEG    TOTAL     TIME
        (d m)    (d/m)    (NM/dg)     (NM)   (NM)     (h:mm)
 -----------------------------------------------------------
  0     MACDILL                         0.      0.     0:01
  1S    26 45    83 12    105/000      76.     76.     0:16
  2S    23 15    83 12    105/180     210.    286.     1:07
  3S    23 46    81 51    105/135      81.    366.     1:27
  4S    26 14    84 34    105/315     210.    576.     2:18
  5S    25 00    85 08    105/270      81.    657.     2:38
  6S    25 00    81 16    105/090     210.    867.     3:29
  7S    26 14    81 50    105/045      81.    948.     3:49
  8S    23 46    84 33    105/225     210.   1158.     4:40
  9S    23 15    83 12    105/180      81.   1238.     5:01
 10S    26 45    83 12    105/000     210.   1448.     5:52
 11     MACDILL                        76.   1524.     6:06
 -----------------------------------------------------------


 ************************************************************************
 MISSION PLAN:  Unknown
 Prepared by the Hurricane Research Division File: current1.ftk
 Aircraft: N42RF
 Proposed takeoff: MACDILL 23/2200Z
 Proposed recovery: MACDILL
 Time to IP:  0:16
 Mission Duration:  6:06
 ***********************************************************************
```

- **drops1.txt**:
```
 ========================================================================
 MISSION PLAN:  Unknown

 Prepared by the Hurricane Research Division File: current1.ftk

 Aircraft: N42RF  Proposed takeoff: 23/2200Z
 ========================================================================


 DROP LOCATIONS

 ==========================================
  #      LAT      LON      RAD/AZM    TIME
        (d m)    (d m)     (NM/dg)   (h:mm)
 ------------------------------------------
  1S    26 45    83 12     105/000    0:16
  2S    23 15    83 12     105/180    1:07
  3S    23 46    81 51     105/135    1:27
  4S    26 14    84 34     105/315    2:18
  5S    25 00    85 08     105/270    2:38
  6S    25 00    81 16     105/090    3:29
  7S    26 14    81 50     105/045    3:49
  8S    23 46    84 33     105/225    4:40
  9S    23 15    83 12     105/180    5:01
 10S    26 45    83 12     105/000    5:52
 ------------------------------------------
```

### EXAMPLE 2
- **current1.ftk**:
```
49 07/1800Z Genesis
H 18.5 82.5 270 15
A MACDILL
  24 83.5 20000
I 4 15000
  23 85.5 10000
  21 85.5 10000
I 4 10000
S 180 330 5000
S 135 330 5000
S 90 330 5000
S 60 330 5000
S 30 330 5000
S 0 0 5000
S 30 150 5000
S 60 150 5000
S 90 150 5000
S 135 150 5000
S 180 150 5000
S 180 90 5000
S 135 90 5000
S 90 90 5000
S 60 90 5000
S 30 90 5000
S 0 0 5000
S 30 270 5000
S 60 270 5000
S 90 270 5000
S 135 270 5000
S 180 270 5000
S 180 210 5000
S 135 210 5000
S 90 210 5000
S 60 210 5000
S 30 210 5000
S 0 0 5000
S 30 30 5000
S 60 30 5000
S 90 30 5000
S 135 30 5000
S 180 30 5000
I 4 10000
  19 77 10000
  19 74.5 10000
  21 73.5 10000
  23 73.5 10000
I 6 10000
  24 77 10000
Z MACDILL
```

- **turns1.txt**:
```
 ========================================================================
 MISSION PLAN:  GENESIS

 Prepared by the Hurricane Research Division File: current1.ftk

 Aircraft: N49RF  Proposed takeoff: 07/1800Z
 ========================================================================


 TRACK DISTANCE TABLE

 ===========================================================
  #      LAT      LON     RAD/AZM     LEG    TOTAL     TIME
        (d m)    (d/m)    (NM/dg)     (NM)   (NM)     (h:mm)
 -----------------------------------------------------------
  0     MACDILL                         0.      0.     0:01
  1     24 00    83 30                237.    237.     0:34
  2     23 00    85 30                126.    363.     0:52
  3     21 00    85 30                120.    483.     1:10
  4S    21 06    84 25    180/330      68.    551.     1:20
  5S    20 27    84 03    135/330      44.    595.     1:27
  6S    19 48    83 42     90/330      44.    639.     1:34
  7S    19 22    83 27     60/330      29.    669.     1:39
  8S    18 56    83 13     30/330      29.    698.     1:44
  9S    18 30    82 58      0/000      29.    727.     1:49
 10S    18 04    82 44     30/150      29.    757.     1:54
 11S    17 38    82 30     60/150      29.    786.     1:59
 12S    17 12    82 15     90/150      29.    816.     2:04
 13S    16 33    81 54    135/150      44.    860.     2:11
 14S    15 54    81 32    180/150      44.    904.     2:18
 15S    18 30    80 03    180/090     177.   1081.     2:43
 16S    18 30    80 52    135/090      47.   1128.     2:50
 17S    18 30    81 42     90/090      47.   1175.     2:58
 18S    18 30    82 15     60/090      31.   1206.     3:03
 19S    18 30    82 48     30/090      31.   1237.     3:08
 20S    18 30    83 21      0/000      31.   1269.     3:13
 21S    18 30    83 54     30/270      31.   1300.     3:19
 22S    18 30    84 27     60/270      31.   1331.     3:24
 23S    18 30    85 00     90/270      31.   1363.     3:29
 24S    18 30    85 49    135/270      47.   1410.     3:36
 25S    18 30    86 38    180/270      47.   1456.     3:44
 26S    15 54    85 10    180/210     177.   1634.     4:09
 27S    16 33    84 48    135/210      44.   1678.     4:16
 28S    17 12    84 26     90/210      44.   1722.     4:23
 29S    17 38    84 12     60/210      29.   1751.     4:28
 30S    18 04    83 57     30/210      29.   1781.     4:33
 31S    18 30    83 43      0/000      29.   1810.     4:38
 32S    18 56    83 29     30/030      29.   1840.     4:43
 33S    19 22    83 14     60/030      29.   1869.     4:48
 34S    19 48    83 00     90/030      29.   1898.     4:53
 35S    20 27    82 38    135/030      44.   1943.     5:00
 36S    21 06    82 16    180/030      44.   1987.     5:07
 37     19 00    77 00                326.   2313.     5:52
 38     19 00    74 30                142.   2455.     6:12
 39     21 00    73 30                133.   2588.     6:31
 40     23 00    73 30                120.   2708.     6:49
 41     24 00    77 00                202.   2910.     7:17
 42     MACDILL                       378.   3288.     8:09
 -----------------------------------------------------------


 ************************************************************************
 MISSION PLAN:  GENESIS
 Prepared by the Hurricane Research Division File: current1.ftk
 Aircraft: N49RF
 Proposed takeoff: MACDILL  07/1800Z
 Proposed recovery: MACDILL
 Time to IP:  0:34
 Mission Duration:  8:09
 ************************************************************************
```

- **drops1.txt**:
```
 ========================================================================
 MISSION PLAN:  GENESIS

 Prepared by the Hurricane Research Division File: current1.ftk

 Aircraft: N49RF  Proposed takeoff: 07/1800Z
 ========================================================================


 DROP LOCATIONS

 ==========================================
  #      LAT      LON      RAD/AZM    TIME
        (d m)    (d m)     (NM/dg)   (h:mm)
 ------------------------------------------
  1     24 00    83 30                0:34
  2I    23 48    83 54                0:38
  3I    23 36    84 18                0:41
  4I    23 24    84 42                0:44
  5I    23 12    85 06                0:48
  6     23 00    85 30                0:52
  7     21 00    85 30                1:10
  8I    21 01    85 13                1:12
  9I    21 02    84 56                1:14
 10I    21 04    84 39                1:16
 11I    21 05    84 22                1:18
 12S    21 06    84 25     180/330    1:20
 13S    20 27    84 03     135/330    1:27
 14S    19 48    83 42      90/330    1:34
 15S    19 22    83 27      60/330    1:39
 16S    18 56    83 13      30/330    1:44
 17S    18 30    82 58       0/000    1:49
 18S    18 04    82 44      30/150    1:54
 19S    17 38    82 30      60/150    1:59
 20S    17 12    82 15      90/150    2:04
 21S    16 33    81 54     135/150    2:11
 22S    15 54    81 32     180/150    2:18
 23S    18 30    80 03     180/090    2:43
 24S    18 30    80 52     135/090    2:50
 25S    18 30    81 42      90/090    2:58
 26S    18 30    82 15      60/090    3:03
 27S    18 30    82 48      30/090    3:08
 28S    18 30    83 21       0/000    3:13
 29S    18 30    83 54      30/270    3:19
 30S    18 30    84 27      60/270    3:24
 31S    18 30    85 00      90/270    3:29
 32S    18 30    85 49     135/270    3:36
 33S    18 30    86 38     180/270    3:44
 34S    15 54    85 10     180/210    4:09
 35S    16 33    84 48     135/210    4:16
 36S    17 12    84 26      90/210    4:23
 37S    17 38    84 12      60/210    4:28
 38S    18 04    83 57      30/210    4:33
 39S    18 30    83 43       0/000    4:38
 40S    18 56    83 29      30/030    4:43
 41S    19 22    83 14      60/030    4:48
 42S    19 48    83 00      90/030    4:53
 43S    20 27    82 38     135/030    5:00
 44S    21 06    82 16     180/030    5:07
 45I    20 41    80 08                5:23
 46I    20 16    79 21                5:30
 47I    19 50    78 34                5:37
 48I    19 25    77 47                5:44
 49     19 00    77 00                5:52
 50     19 00    74 30                6:12
 51     21 00    73 30                6:31
 52     23 00    73 30                6:49
 53I    23 09    74 00                6:53
 54I    23 17    74 30                6:57
 55I    23 26    75 00                7:01
 56I    23 34    75 30                7:04
 57I    23 43    76 00                7:08
 58I    23 51    76 30                7:12
 59     24 00    77 00                7:17
 ------------------------------------------
```

### EXAMPLE 3

- **current1.ftk**:
```
49 04/1730Z BONNIE
H 14.0 65.7 0 0
A ST CROIX
  18.761 64.013 45000
  17.786 62.542 45000
  17.100 59.000 45000
  18.067 57.058 45000
  19.950 57.078 45000
  20.068 58.942 45000
  21.978 59.046 45000
  23.003 61.004 45000
  23.991 63.009 45000
  24.000 65.004 45000
  23.867 66.915 45000
  22.002 66.093 45000
  20.999 68.002 45000
  19.865 69.838 45000
  18.272 68.405 45000
  17.089 69.355 45000
  15.480 68.129 45000
  14.894 69.928 45000
  13.095 68.936 45000
  14.162 67.486 45000
  13.187 65.975 45000
  13.161 64.099 45000
  14.192 63.529 45000
Z BARBADOS
```

- **turns1.txt**:
```
 ========================================================================
 MISSION PLAN:  BONNIE

 Prepared by the Hurricane Research Division File: current1.ftk

 Aircraft: N49RF  Proposed takeoff: 04/1730Z
 ========================================================================


 TRACK DISTANCE TABLE

 ===========================================================
  #      LAT      LON     RAD/AZM     LEG    TOTAL     TIME
        (d m)    (d/m)    (NM/dg)     (NM)   (NM)     (h:mm)
 -----------------------------------------------------------
  0     ST CROIX                        0.      0.     0:01
  1     18 46    64 01                 78.     78.     0:13
  2     17 47    62 33                102.    180.     0:27
  3     17 06    59 00                207.    388.     0:57
  4     18 04    57 03                126.    513.     1:15
  5     19 57    57 05                113.    626.     1:31
  6     20 04    58 57                106.    732.     1:46
  7     21 59    59 03                115.    847.     2:03
  8     23 00    61 00                125.    972.     2:21
  9     23 59    63 01                125.   1097.     2:39
 10     24 00    65 00                110.   1207.     2:55
 11     23 52    66 55                105.   1312.     3:10
 12     22 00    66 06                121.   1433.     3:28
 13     21 00    68 00                123.   1556.     3:45
 14     19 52    69 50                124.   1680.     4:03
 15     18 16    68 24                126.   1805.     4:21
 16     17 05    69 21                 90.   1895.     4:34
 17     15 29    68 08                120.   2015.     4:52
 18     14 54    69 56                110.   2125.     5:07
 19     13 06    68 56                123.   2247.     5:25
 20     14 10    67 29                106.   2354.     5:41
 21     13 11    65 58                106.   2460.     5:56
 22     13 10    64 06                110.   2569.     6:12
 23     14 12    63 32                 70.   2640.     6:22
 24     BARBADOS                      246.   2885.     6:57
 -----------------------------------------------------------


 ************************************************************************
 MISSION PLAN:  BONNIE
 Prepared by the Hurricane Research Division File: current1.ftk
 Aircraft: N49RF
 Proposed takeoff: ST CROIX  04/1730Z
 Proposed recovery: BARBADOS
 Time to IP:  0:13
 Mission Duration:  6:57
 ************************************************************************
```

- **drops1.txt**:
```
 ========================================================================
 MISSION PLAN:  BONNIE

 Prepared by the Hurricane Research Division File: current1.ftk

 Aircraft: N49RF  Proposed takeoff: 04/1730Z
 ========================================================================


 DROP LOCATIONS

 ==========================================
  #      LAT      LON      RAD/AZM    TIME
        (d m)    (d m)     (NM/dg)   (h:mm)
 ------------------------------------------
  1     18 46    64 01                0:13
  2     17 47    62 33                0:27
  3     17 06    59 00                0:57
  4     18 04    57 03                1:15
  5     19 57    57 05                1:31
  6     20 04    58 57                1:46
  7     21 59    59 03                2:03
  8     23 00    61 00                2:21
  9     23 59    63 01                2:39
 10     24 00    65 00                2:55
 11     23 52    66 55                3:10
 12     22 00    66 06                3:28
 13     21 00    68 00                3:45
 14     19 52    69 50                4:03
 15     18 16    68 24                4:21
 16     17 05    69 21                4:34
 17     15 29    68 08                4:52
 18     14 54    69 56                5:07
 19     13 06    68 56                5:25
 20     14 10    67 29                5:41
 21     13 11    65 58                5:56
 22     13 10    64 06                6:12
 23     14 12    63 32                6:22
 ------------------------------------------
```
