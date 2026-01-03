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

# Arc Network Settings
IS_ARC = str(os.getenv("ARC_NETWORK", "TRUE")).strip().lower() == "true"
wib = pytz.timezone('Asia/Jakarta')

class GM:
    def __init__(self) -> None:
        self.BASE_API = "https://zevzyzupcazraidfuegn.supabase.co/rest/v1"
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
                "amount": 0.5,
            },
            "gas_fee": 1.0
        }
        self.CONTRACT_ABI = [
            {"type": "function", "name": "timeUntilNextGM", "stateMutability": "view", "inputs": [{"internalType": "address", "name": "user", "type": "address"}], "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}]},
            {"type": "function", "name": "GM_FEE", "stateMutability": "view", "inputs": [], "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}]},
            {"type": "function", "name": "onChainGM", "stateMutability": "payable", "inputs": [{"internalType": "address", "name": "referrer", "type": "address"}], "outputs": []},
            {"type": "function", "name": "deploy", "stateMutability": "payable", "inputs": [], "outputs": []}
        ]
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.deploy_count = 0

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL} | {message}", flush=True)

    def welcome(self):
        print(f"{Fore.GREEN + Style.BRIGHT}Arc Testnet {Fore.BLUE + Style.BRIGHT}Auto BOT")

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    async def load_proxies(self):
        filename = "proxy.txt"
        if not os.path.exists(filename):
            self.log(f"{Fore.RED}proxy.txt file မတွေ့ပါ။")
            return
        with open(filename, 'r') as f:
            self.proxies = [line.strip() for line in f if line.strip()]
        self.log(f"{Fore.GREEN}Total Proxies: {len(self.proxies)}")

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        return proxies if any(proxies.startswith(s) for s in schemes) else f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if not self.proxies: return None
        if account not in self.account_proxies:
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies: return None
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        return proxy

    def build_proxy_config(self, proxy=None):
        if not proxy: return None, None, None
        if proxy.startswith("socks"):
            return ProxyConnector.from_url(proxy), None, None
        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                user, pw, hp = match.groups()
                return None, f"http://{hp}", BasicAuth(user, pw)
            return None, proxy, None
        return None, None, None

    def generate_address(self, account_key):
        try: return Account.from_key(account_key).address
        except: return None

    def mask_account(self, address):
        return f"{address[:6]}******{address[-6:]}" if address else "Unknown"

    async def get_web3_with_check(self, address, network, use_proxy):
        req_kwargs = {"timeout": 60}
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        if use_proxy and proxy:
            req_kwargs["proxies"] = {"http": proxy, "https": proxy}
        web3 = Web3(Web3.HTTPProvider(network["rpc_url"], request_kwargs=req_kwargs))
        return web3

    async def get_token_balance(self, address, network, use_proxy):
        try:
            web3 = await self.get_web3_with_check(address, network, use_proxy)
            return web3.from_wei(web3.eth.get_balance(address), "ether")
        except: return None

    async def time_until_next_gm(self, address, network, use_proxy):
        try:
            web3 = await self.get_web3_with_check(address, network, use_proxy)
            contract = web3.eth.contract(address=web3.to_checksum_address(network["onchain_gm"]["contract"]), abi=self.CONTRACT_ABI)
            return contract.functions.timeUntilNextGM(address).call()
        except: return 0

    async def gm_fee(self, address, network, use_proxy):
        try:
            web3 = await self.get_web3_with_check(address, network, use_proxy)
            contract = web3.eth.contract(address=web3.to_checksum_address(network["onchain_gm"]["contract"]), abi=self.CONTRACT_ABI)
            return contract.functions.GM_FEE().call()
        except: return 0

    async def perform_gm(self, account, address, network, gm_fee, use_proxy):
        try:
            web3 = await self.get_web3_with_check(address, network, use_proxy)
            contract = web3.eth.contract(address=web3.to_checksum_address(network["onchain_gm"]["contract"]), abi=self.CONTRACT_ABI)
            gm_tx = contract.functions.onChainGM(address).build_transaction({
                "from": address, "value": gm_fee, "nonce": web3.eth.get_transaction_count(address),
                "gas": 200000, "maxFeePerGas": web3.to_wei(network["gas_fee"], "gwei"),
                "maxPriorityFeePerGas": web3.to_wei(network["gas_fee"], "gwei"), "chainId": network["network_id"]
            })
            signed = web3.eth.account.sign_transaction(gm_tx, account)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return web3.to_hex(tx_hash), receipt.blockNumber
        except Exception as e:
            self.log(f"{Fore.RED}GM Failed: {str(e)}")
            return None, None

    def print_question(self):
        print(f"{Fore.GREEN}1. Onchain GM\n2. Deploy Contract\n3. Run All Features")
        option = int(input(f"{Fore.BLUE}Choose [1/2/3] -> ").strip())
        if option in [2, 3]:
            self.deploy_count = int(input(f"{Fore.YELLOW}Enter Deploy Count -> ").strip())
        print(f"{Fore.WHITE}1. Run With Proxy\n2. Run Without Proxy")
        proxy_choice = int(input(f"{Fore.BLUE}Choose [1/2] -> ").strip())
        rotate_proxy = input(f"{Fore.BLUE}Rotate Invalid Proxy? [y/n] -> ").strip().lower() == 'y' if proxy_choice == 1 else False
        return option, proxy_choice, rotate_proxy

    async def process_accounts(self, account, address, enabled_networks, option, use_proxy, rotate_proxy):
        for network in enabled_networks:
            self.log(f"Network: {network['network_name']}")
            if option in [1, 3]:
                wait_time = await self.time_until_next_gm(address, network, use_proxy)
                if wait_time > 0:
                    self.log(f"{Fore.YELLOW}GM already done. Next in {wait_time}s")
                else:
                    fee = await self.gm_fee(address, network, use_proxy)
                    tx, block = await self.perform_gm(account, address, network, fee, use_proxy)
                    if tx: self.log(f"{Fore.GREEN}GM Success! Block: {block} | Tx: {tx}")

    async def main(self):
        try:
            with open('accounts.txt', 'r') as f:
                accounts = [line.strip() for line in f if line.strip()]
            option, proxy_choice, rotate_proxy = self.print_question()
            use_proxy = (proxy_choice == 1)
            
            while True:
                self.clear_terminal()
                self.welcome()
                for acc in accounts:
                    addr = self.generate_address(acc)
                    if not addr: continue
                    self.log(f"--- [ {self.mask_account(addr)} ] ---")
                    await self.process_accounts(acc, addr, [self.ARC_NETWORK], option, use_proxy, rotate_proxy)
                
                self.log("All accounts processed. Waiting 24h...")
                await asyncio.sleep(24 * 3600)
        except Exception as e:
            self.log(f"Error: {e}")

if __name__ == "__main__":
    bot = GM()
    asyncio.run(bot.main())
