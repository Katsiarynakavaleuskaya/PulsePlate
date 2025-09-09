# CRON Setup for Food Database Updates

## RU: Настройка CRON для обновления базы данных продуктов
## EN: CRON Setup for Food Database Updates

To automatically update the food database weekly, add the following entry to your crontab:

```bash
# Run every Sunday at 2:00 AM
0 2 * * 0 /usr/bin/python3 /path/to/PulsePlate/scripts/schedule_food_db_update.py >> /path/to/PulsePlate/logs/cron.log 2>&1
```

### How to set up CRON:

1. Open your crontab:
   ```bash
   crontab -e
   ```

2. Add the CRON entry above, adjusting the paths to match your installation

3. Save and exit

### CRON Entry Format:
```
* * * * * command
│ │ │ │ │
│ │ │ │ └── Day of week (0-7, where 0 and 7 are Sunday)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

### Example for daily updates at 3:30 AM:
```bash
30 3 * * * /usr/bin/python3 /path/to/PulsePlate/scripts/schedule_food_db_update.py >> /path/to/PulsePlate/logs/cron.log 2>&1
```

### Notes:
- Make sure the script paths are absolute
- Ensure the user running the CRON job has the necessary permissions
- Logs will be written to `/path/to/PulsePlate/logs/food_db_update.log`
- The CRON log will capture any CRON-related issues