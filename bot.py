from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account
from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from dotenv import load_dotenv
from colorama import *
import asyncio, random, time, json, re, os, pytz

load_dotenv()

# Arc Network Only
IS_ARC = str(os.getenv("ARC_NETWORK", "TRUE")).strip().lower() == "true"

wib = pytz.timezone('Asia/Jakarta')

class GM:
    def __init__(self) -> None:
        self.BASE_API = "https://zevzyzupcazraidfuegn.supabase.co/rest/v1"
        
        # Arc Testnet Configuration Updated
        self.ARC_NETWORK = {
            "network_name": "Arc Testnet",
            "ticker": "USDC", 
            "rpc_url": "https://rpc.testnet.arc.network", 
            "explorer": "https://testnet.arcscan.app/tx/",
            "network_id": 5042002, 
            "onchain_gm": {
                "contract": "0x363cC75a89aE5673b427a1Fa98AFc48FfDE7Ba43" 
            },
            "deploy": {
                "contract": "0x363cC75a89aE5673b427a1Fa98AFc48FfDE7Ba43",
                "amount": 0.0001, # လိုအပ်သလို ပြင်နိုင်ပါတယ်
            },
            "gas_fee": 1.0 # Testnet gas price အပေါ်မူတည်ပြီး လိုအပ်ရင် တိုး/လျော့ လုပ်ပါ
        }

        self.CONTRACT_ABI = [
            {
                "type": "function",
                "name": "timeUntilNextGM",
                "stateMutability": "view",
                "inputs": [{ "internalType": "address", "name": "user", "type": "address" }],
                "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }]
            },
            {
                "type": "function",
                "name": "GM_FEE",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }]
            },
            {
                "type": "function",
                "name": "onChainGM",
                "stateMutability": "payable",
                "inputs": [{ "internalType": "address", "name": "referrer", "type": "address" }],
                "outputs": []
            },
            {
                "type": "function",
                "name": "deploy",
                "stateMutability": "payable",
                "inputs": [],
                "outputs": []
            },
        ]
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.deploy_count = 0

    # ... [Helper Functions remain the same] ...

    def log(self, message):
        print(f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL} | {message}", flush=True)

    def welcome(self):
        print(f"{Fore.GREEN + Style.BRIGHT}Arc Testnet GM {Fore.BLUE + Style.BRIGHT}Auto BOT")

    # [ ... Rest of the functions like perform_gm, process_accounts, etc. ... ]

    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]

            # Arc Network သီးသန့်ပဲ Run ဖို့
            enabled_networks = [self.ARC_NETWORK]

            option, proxy_choice, rotate_proxy = self.print_question()
            use_proxy = True if proxy_choice == 1 else False

            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                self.welcome()
                self.log(f"{Fore.GREEN + Style.BRIGHT}Accounts Total: {len(accounts)}")

                if use_proxy:
                    await self.load_proxies()
                
                separator = "=" * 25
                for account in accounts:
                    address = Account.from_key(account).address
                    self.log(f"{Fore.CYAN + Style.BRIGHT}{separator}[ {address[:6]}...{address[-6:]} ]{separator}")
                    
                    # Header update with your specific key
                    self.HEADERS[address] = {
                        "Accept": "*/*",
                        "Apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", # original key နေရာ
                        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", # original key နေရာ
                        "User-Agent": FakeUserAgent().random,
                    }

                    await self.process_accounts(account, address, enabled_networks, option, use_proxy, rotate_proxy)
                    await asyncio.sleep(3)

                # Wait for 24 hours
                seconds = 24 * 60 * 60
                while seconds > 0:
                    print(f"{Fore.YELLOW}Next Round in: {int(seconds//3600):02d}:{int((seconds%3600)//60):02d}:{int(seconds%60):02d}", end="\r")
                    await asyncio.sleep(1)
                    seconds -= 1

        except Exception as e:
            self.log(f"{Fore.RED}Error: {e}")

if __name__ == "__main__":
    bot = GM()
    asyncio.run(bot.main())
