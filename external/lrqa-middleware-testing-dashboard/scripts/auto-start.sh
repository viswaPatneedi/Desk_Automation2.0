#!/bin/bash
# Auto-start RDK Dashboard on system boot
# Add this to: /etc/cron.d/rdk-dashboard-autostart
# Or run at startup via @reboot cron job

cd /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard
/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard/start-app.sh start
