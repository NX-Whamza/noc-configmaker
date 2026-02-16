# NextLink MikroTik Engineering Compliance Baseline
# Source: Engineering standard script (RouterOS v7.19.4+)
# This file is loaded by backend and appended to generated/migrated configs.
# Baseline RFC blocks are expanded below at runtime.

# VARIABLES
:global LoopIP "__LOOP_IP__"
:global curDate [/system clock get date]
:global curTime [/system clock get time]
:global CurDT ($curDate . " " . $curTime)

# IP SERVICES (engineering baseline)
/ip service set telnet disabled=yes port=5023
/ip service set ftp disabled=yes port=5021
/ip service set www disabled=yes port=1234
/ip service set api disabled=yes
/ip service set api-ssl disabled=yes
/ip service set www-ssl disabled=yes port=443
/ip service set winbox port=8291 address="" disabled=no
/ip service set ssh port=22 address="" disabled=no

# BASELINE COMPLIANCE BLOCKS
{{NEXTLINK_RFC_BLOCKS}}

# SYS NOTE
/system note set note="COMPLIANCE SCRIPT LAST RUN ON $CurDT"
