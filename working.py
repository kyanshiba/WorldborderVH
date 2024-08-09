import asyncio
import logging
from datetime import datetime
from ampapi.modules.ADS import ADS

# Configuration
API_URL = "http://localhost:8080/"
API_USERNAME = "DOGCAT"
API_PASSWORD = "PASS"
INSTANCE_NAME = "INSTANCE"
CHECK_INTERVAL = 10  # seconds
OPEN_VAULT_WAIT_COUNTS = 180 // CHECK_INTERVAL
RETRY_INTERVAL = 20  # seconds (time to wait before retrying after a failure)

border_check = 0
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
        players_in_vault = {}
        open_vault_wait_counter = 0

        while True:
            try:
                # Get current status and console entries
                currentStatus = await Hub.Core.GetUpdatesAsync()
                console = currentStatus.ConsoleEntries

                # Check for matching messages in the console
                for msg in console:
                    if msg.Type == "Console" and msg.Source == "Server thread/INFO":
                        player_name = ""
                        log_content = msg.Contents
                        if "completed" in log_content and "Vault!" in log_content:
                            logging.info(f"Matched message: {log_content}")
                            counter += 4
                            player_name = log_content.split("completed")[0]
                            del players_in_vault[player_name]
                        elif "survived" in log_content and "Vault" in log_content:
                            player_name = log_content.split("survived")[0]
                            del players_in_vault[player_name]
                        elif "was defeated" in log_content and "Vault" in log_content:
                            player_name = log_content.split("was defeated")[0]
                            del players_in_vault[player_name]
                        elif "entered" in log_content and "Vault" in log_content:
                            player_name = log_content.split("entered")[0]
                            # only the existence of the key matters, the value may be useful for logging
                            players_in_vault[player_name] = datetime.now()
                        elif "opened" in log_content and "Vault" in log_content:
                            open_vault_wait_counter = OPEN_VAULT_WAIT_COUNTS

                # Update world borders if needed
                border_check += CHECK_INTERVAL
                if counter != 0 and open_vault_wait_counter <= 0 and len(players_in_vault) == 0:
                    await Hub.Core.SendConsoleMessageAsync(f"dimworldborder minecraft:the_nether add {counter}")
                    await Hub.Core.SendConsoleMessageAsync(f"dimworldborder minecraft:the_end add {counter}")
                    await Hub.Core.SendConsoleMessageAsync(f"dimworldborder minecraft:overworld add {counter}")
                    await Hub.Core.SendConsoleMessageAsync(f"say World Border Increased By: {counter}")
                    logging.info(f"World borders increased by: {counter}")
                    counter = 0
                    border_check = 0
                elif open_vault_wait_counter <= 0 and border_check >= 60 and len(players_in_vault) != 0:
                    logging.info(f"World border counter is: {counter}")
                    logging.info(players_in_vault)
                    border_check = 0
                elif open_vault_wait_counter > 0:
                    open_vault_wait_counter -= 1
                
                    

                # Sleep before checking again
                
                await asyncio.sleep(CHECK_INTERVAL)

            except Exception as e:
                logging.error(f"Error during update check: {e}. Retrying in {RETRY_INTERVAL} seconds.")
                await asyncio.sleep(RETRY_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main_loop())
