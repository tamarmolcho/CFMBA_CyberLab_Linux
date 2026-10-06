#!/bin/bash
# CFMBA ADMINISTRATION MENU
E='echo -e';e='echo -en';trap "R;exit" 2
ESC=$( $e "\e")
TPUT(){ $e "\e[${1};${2}H";}
CLEAR(){ $e "\ec";}
CIVIS(){ $e "\e[?25l";}
DRAW(){ $e "\e%@\e(0";}
WRITE(){ $e "\e(B";}
MARK(){ $e "\e[7m";}
UNMARK(){ $e "\e[27m";}
R(){ CLEAR ;stty sane;$e "\ec\e[37;44m\e[J";};
HEAD(){ DRAW
        for each in $(seq 1 14);do
        $E "   x                                          x"
        done
        WRITE;MARK;TPUT 1 5
        $E "CFMBA ADMINISTRATION MENU                       ";UNMARK;}
        i=0; CLEAR; CIVIS;NULL=/dev/null
FOOT(){ MARK;TPUT 14 5
        printf "ENTER - SELECT,NEXT                       ";UNMARK;}
ARROW(){ read -s -n3 key 2>/dev/null >&2
        if [[ $key = $ESC[A ]];then echo up;fi
        if [[ $key = $ESC[B ]];then echo dn;fi;}
M0(){ TPUT  4 20; $e "Disk Status";}
M1(){ TPUT  5 20; $e "Import";}
M2(){ TPUT  6 20; $e "Stop VM";}
M3(){ TPUT  7 20; $e "Start VM";}
M4(){ TPUT  8 20; $e "Running VMS";}
M5(){ TPUT  9 20; $e "Virtual Machines  ";}
M6(){ TPUT 10 20; $e "Take Screenshot  ";}
M7(){ TPUT 11 20; $e "EXIT   ";}
LM=7
MENU(){ for each in $(seq 0 $LM);do M${each};done;}
POS(){ if [[ $cur == up ]];then ((i--));fi
        if [[ $cur == dn ]];then ((i++));fi
        if [[ $i -lt 0   ]];then i=$LM;fi
        if [[ $i -gt $LM ]];then i=0;fi;}
REFRESH(){ after=$((i+1)); before=$((i-1))
        if [[ $before -lt 0  ]];then before=$LM;fi
        if [[ $after -gt $LM ]];then after=0;fi
        if [[ $j -lt $i      ]];then UNMARK;M$before;else UNMARK;M$after;fi
        if [[ $after -eq 0 ]] || [ $before -eq $LM ];then
        UNMARK; M$before; M$after;fi;j=$i;UNMARK;M$before;M$after;}
INIT(){ R;HEAD;FOOT;MENU;}
SC(){ REFRESH;MARK;$S;$b;cur=`ARROW`;}
ES(){ MARK;$e "ENTER = main menu ";$b;read;INIT;};INIT
BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [[ "$O" != " " ]]; do case $i in
    0) S=M0;SC;if [[ $cur == "" ]];then R;$e "\n$(df -h        )\n";ES;fi;;
    1) S=M1;SC;if [[ $cur == "" ]];then R;$e "\n$("$BIN_DIR/importvm.sh" )\n";ES;fi;;
    2) S=M2;SC;if [[ $cur == "" ]];then R;$e "\n$("$BIN_DIR/stopvm.sh"    )\n";ES;fi;;
    3) S=M3;SC;if [[ $cur == "" ]];then R;$e "\n$("$BIN_DIR/startvm.sh" )\n";ES;fi;;
    4) S=M4;SC;if [[ $cur == "" ]];then R;$e "\n$(vboxmanage list runningvms     )\n";ES;fi;;
    5) S=M5;SC;if [[ $cur == "" ]];then R;$e "\n$(vboxmanage list vms)\n";ES;fi;;
    6) S=M6;SC;if [[ $cur == "" ]];then R;$e "\n$("$BIN_DIR/takescreenvm.sh"  )\n";ES;fi;;
    7) S=M7;SC;if [[ $cur == "" ]];then R;exit 0;fi;;
esac;POS;done
