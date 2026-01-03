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
            "gas_fee": 1.0 
        }
        self.REFERRER = "0xc2fcFd1bF7CB2Cdd14A9B0dADB4FdcB845219D01"
        
        self.CONTRACT_ABI = [
            {"type": "function", "name": "timeUntilNextGM", "stateMutability": "view", "inputs": [{"internalType": "address", "name": "user", "type": "address"}], "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}]},
            {"type": "function", "name": "GM_FEE", "stateMutability": "view", "inputs": [], "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}]},
            {"type": "function", "name": "onChainGM", "stateMutability": "payable", "inputs": [{"internalType": "address", "name": "referrer", "type": "address"}], "outputs": []}
        ]
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}

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

    async def get_web3(self, network):
        return Web3(Web3.HTTPProvider(network["rpc_url"], request_kwargs={"timeout": 60}))

    async def perform_gm(self, account_key, address, network):
        try:
            web3 = await self.get_web3(network)
            contract_addr = web3.to_checksum_address(network["onchain_gm"]["contract"])
            referrer_addr = web3.to_checksum_address(self.REFERRER)
            contract = web3.eth.contract(address=contract_addr, abi=self.CONTRACT_ABI)
            
            # 1. Check Cool-down
            self.log("Checking GM status...")
            wait_time = contract.functions.timeUntilNextGM(address).call()
            if wait_time > 0:
                self.log(f"{Fore.YELLOW}GM already performed. Wait for: {self.format_seconds(wait_time)}")
                return None

            # 2. Fixed Fee 0.5 USDC (Scaling by 10^18 for Wei)
            fee = web3.to_wei(0.5, 'ether') 
            self.log(f"GM Fee set to: 0.5 {network['ticker']}")

            # 3. Transaction Preparation
            nonce = web3.eth.get_transaction_count(address)
            gas_price = web3.eth.gas_price
            
            # 4. Gas Estimation to prevent Revert Failures
            try:
                gas_limit = contract.functions.onChainGM(referrer_addr).estimate_gas({
                    "from": address, "value": fee, "nonce": nonce
                })
                gas_limit = int(gas_limit * 1.2) # Add 20% buffer
            except Exception as e:
                self.log(f"{Fore.RED}Gas Estimation Failed (Potential Revert): {str(e)}")
                return None

            gm_tx = contract.functions.onChainGM(referrer_addr).build_transaction({
                "from": address,
                "value": fee,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": int(gas_price * 1.1), # 10% tip for speed
                "chainId": network["network_id"]
            })
            
            # 5. Signing and Sending
            signed = web3.eth.account.sign_transaction(gm_tx, account_key)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            
            self.log(f"Tx Sent: {web3.to_hex(tx_hash)}. Waiting for confirmation...")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt.status == 1:
                return web3.to_hex(tx_hash), receipt.blockNumber
            else:
                self.log(f"{Fore.RED}Transaction Failed on Blockchain.")
                return None
                
        except Exception as e:
            self.log(f"{Fore.RED}Error: {str(e)}")
            return None

    def print_question(self):
        print(f"{Fore.GREEN}1. Onchain GM Only\n2. Run Loop (24h)")
        option = int(input(f"{Fore.BLUE}Choose [1/2] -> ").strip())
        return option

    async def main(self):
        try:
            with open('accounts.txt', 'r') as f:
                accounts = [line.strip() for line in f if line.strip()]
            
            option = self.print_question()
            
            while True:
                self.clear_terminal()
                self.welcome()
                self.log(f"Total Accounts: {len(accounts)}")

                for acc in accounts:
                    try:
                        address = Account.from_key(acc).address
                        self.log(f"--- [ {address[:6]}...{address[-6:]} ] ---")
                        
                        web3 = await self.get_web3(self.ARC_NETWORK)
                        balance = web3.from_wei(web3.eth.get_balance(address), 'ether')
                        self.log(f"Balance: {balance} {self.ARC_NETWORK['ticker']}")

                        if balance < 0.5:
                            self.log(f"{Fore.RED}Insufficient balance for GM fee (0.5).")
                            continue

                        result = await self.perform_gm(acc, address, self.ARC_NETWORK)
                        if result:
                            tx, block = result
                            self.log(f"{Fore.GREEN}Success! Block: {block} | Tx: {tx}")
                        
                        await asyncio.sleep(5)
                    except Exception as e:
                        self.log(f"{Fore.RED}Account Process Error: {e}")

                if option == 1:
                    self.log("All accounts finished.")
                    break
                
                self.log("Iteration complete. Sleeping for 24 hours...")
                await asyncio.sleep(24 * 3600)
        except Exception as e:
            self.log(f"Main Loop Error: {e}")

if __name__ == "__main__":
    bot = GM()
    asyncio.run(bot.main())
