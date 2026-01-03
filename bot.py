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
                "contract": "0xa3d9Fbd0edB10327ECB73D2C72622E505dF468a2",
                "amount": 1,
            },
            "gas_fee": 1.0 # Gwei
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
        if not os.path.exists(filename): return
        with open(filename, 'r') as f:
            self.proxies = [line.strip() for line in f if line.strip()]
        self.log(f"{Fore.GREEN}Total Proxies: {len(self.proxies)}")

    def get_next_proxy_for_account(self, account):
        if not self.proxies: return None
        if account not in self.account_proxies:
            proxy = self.proxies[self.proxy_index]
            if not any(proxy.startswith(s) for s in ["http://", "https://", "socks4://", "socks5://"]):
                proxy = f"http://{proxy}"
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    async def get_web3_with_check(self, address, network):
        # Proxy handling simple version for reliability
        web3 = Web3(Web3.HTTPProvider(network["rpc_url"], request_kwargs={"timeout": 60}))
        if web3.is_connected():
            return web3
        raise Exception("RPC ချိတ်ဆက်မှု မအောင်မြင်ပါ။")

    async def get_token_balance(self, web3, address, network):
        try:
            balance = web3.eth.get_balance(address)
            return web3.from_wei(balance, "ether")
        except: return 0

    async def perform_gm(self, account_key, address, network, use_proxy):
        try:
            web3 = await self.get_web3_with_check(address, network)
            contract_addr = web3.to_checksum_address(network["onchain_gm"]["contract"])
            contract = web3.eth.contract(address=contract_addr, abi=self.CONTRACT_ABI)
            
            # Check GM Status first
            self.log("GM Status စစ်ဆေးနေသည်...")
            wait_time = contract.functions.timeUntilNextGM(address).call()
            if wait_time > 0:
                self.log(f"{Fore.YELLOW}GM လုပ်ပြီးသားဖြစ်နေသည်။ စောင့်ရန်အချိန်: {self.format_seconds(wait_time)}")
                return None

            fee = contract.functions.GM_FEE().call()
            self.log(f"GM Fee: {fee} wei. Transaction ပို့နေသည်...")

            nonce = web3.eth.get_transaction_count(address)
            gas_price = web3.eth.gas_price
            
            gm_tx = contract.functions.onChainGM(address).build_transaction({
                "from": address,
                "value": fee,
                "nonce": nonce,
                "gas": 250000,
                "gasPrice": int(gas_price * 1.1), # Gas Price ကို ၁၀% ပိုပေးထားသည်
                "chainId": network["network_id"]
            })
            
            signed = web3.eth.account.sign_transaction(gm_tx, account_key)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            
            self.log(f"Tx Hash: {web3.to_hex(tx_hash)}. Confirm ဖြစ်သည်အထိ စောင့်နေသည်...")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            return web3.to_hex(tx_hash), receipt.blockNumber
        except Exception as e:
            self.log(f"{Fore.RED}GM Error: {str(e)}")
            return None, None

    def print_question(self):
        print(f"{Fore.GREEN}1. Onchain GM\n2. Deploy Contract\n3. Run All Features")
        option = int(input(f"{Fore.BLUE}Choose [1/2/3] -> ").strip())
        if option in [2, 3]:
            self.deploy_count = int(input(f"{Fore.YELLOW}Enter Deploy Count -> ").strip())
        print(f"{Fore.WHITE}1. Run With Proxy\n2. Run Without Proxy")
        proxy_choice = int(input(f"{Fore.BLUE}Choose [1/2] -> ").strip())
        return option, proxy_choice

    async def main(self):
        try:
            if not os.path.exists('accounts.txt'):
                self.log(f"{Fore.RED}accounts.txt မတွေ့ပါ။")
                return
            with open('accounts.txt', 'r') as f:
                accounts = [line.strip() for line in f if line.strip()]
            
            option, proxy_choice = self.print_question()
            use_proxy = (proxy_choice == 1)
            
            while True:
                self.clear_terminal()
                self.welcome()
                self.log(f"စုစုပေါင်း Account: {len(accounts)}")
                if use_proxy: await self.load_proxies()

                for acc in accounts:
                    try:
                        address = Account.from_key(acc).address
                        self.log(f"{Fore.WHITE + Style.BRIGHT}--- [ {address[:6]}...{address[-6:]} ] ---")
                        
                        web3 = await self.get_web3_with_check(address, self.ARC_NETWORK)
                        balance = await self.get_token_balance(web3, address, self.ARC_NETWORK)
                        self.log(f"Balance: {balance} {self.ARC_NETWORK['ticker']}")

                        if option in [1, 3]:
                            result = await self.perform_gm(acc, address, self.ARC_NETWORK, use_proxy)
                            if result:
                                tx, block = result
                                self.log(f"{Fore.GREEN}အောင်မြင်သည်။ Block: {block}")
                        
                        await asyncio.sleep(3)
                    except Exception as e:
                        self.log(f"{Fore.RED}Account Error: {e}")

                self.log(f"{Fore.CYAN}အကုန်ပြီးပါပြီ။ ၂၄ နာရီ စောင့်ပါမည်...")
                await asyncio.sleep(24 * 3600)
        except Exception as e:
            self.log(f"Main Error: {e}")

if __name__ == "__main__":
    bot = GM()
    asyncio.run(bot.main())
