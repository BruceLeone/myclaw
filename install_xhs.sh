#!/bin/bash
result=$(clawhub install xhs 2>&1)
openclaw message send --channel qqbot --to 248538E38E2B0798FD668846A3855E19 --message "xhs技能安装重试结果：
$result"
