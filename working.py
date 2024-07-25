import asyncio
import logging
from ampapi.modules.ADS import ADS

# Configuration
API_URL = "http://localhost:8080/"
API_USERNAME = "DOGCAT"
API_PASSWORD = "PASS"
INSTANCE_NAME = "INSTANCE"
CHECK_INTERVAL = 10  # seconds
RETRY_INTERVAL = 20  # seconds (time to wait before retrying after a failure)

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def connect_to_api():
    try:
        API = ADS(API_URL, API_USERNAME, API_PASSWORD)
        await API.LoginAsync()
        logging.info("Logged in to API")
        return API
    except Exception as e:
        logging.error(f"Error connecting to API: {e}")
        return None

async def get_instance(API):
    try:
        targets = await API.ADSModule.GetInstancesAsync()
        target = targets[0]

        instances = target.AvailableInstances
        for instance in instances:
            if instance.InstanceName == INSTANCE_NAME:
                return instance.InstanceID
        logging.error(f"Instance {INSTANCE_NAME} not found")
        return None
    except Exception as e:
        logging.error(f"Error getting instance: {e}")
        return None

async def main_loop():
    while True:
        API = await connect_to_api()
        if not API:
            await asyncio.sleep(RETRY_INTERVAL)
            continue

        hub_instance_id = await get_instance(API)
        if not hub_instance_id:
            await asyncio.sleep(RETRY_INTERVAL)
            continue

        Hub = await API.InstanceLoginAsync(hub_instance_id, "Minecraft")
        logging.info(f"Logged in to instance {INSTANCE_NAME}")

        counter = 0

        while True:
            try:
                # Get current status and console entries
                currentStatus = await Hub.Core.GetUpdatesAsync()
                console = currentStatus.ConsoleEntries

                # Check for matching messages in the console
                for msg in console:
                    if msg.Type == "Console" and msg.Source == "Server thread/INFO":
                        log_content = msg.Contents
                        if "completed" in log_content and "Vault!" in log_content:
                            logging.info(f"Matched message: {log_content}")
                            counter += 4

                # Update world borders if needed
                if counter != 0:
                    await Hub.Core.SendConsoleMessageAsync(f"dimworldborder minecraft:the_nether add {counter}")
                    await Hub.Core.SendConsoleMessageAsync(f"dimworldborder minecraft:the_end add {counter}")
                    await Hub.Core.SendConsoleMessageAsync(f"dimworldborder minecraft:overworld add {counter}")
                    await Hub.Core.SendConsoleMessageAsync(f"say World Border Increased By: {counter}")
                    logging.info(f"World borders increased by: {counter}")
                    counter = 0

                # Sleep before checking again
                await asyncio.sleep(CHECK_INTERVAL)

            except Exception as e:
                logging.error(f"Error during update check: {e}. Retrying in {RETRY_INTERVAL} seconds.")
                await asyncio.sleep(RETRY_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main_loop())