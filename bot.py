from web3 import Web3
from eth_account import Account
from datetime import datetime
from dotenv import load_dotenv
from colorama import *
import asyncio, os, pytz, aiohttp, json

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
            "onchain_gm": {"contract": "0x363cC75a89aE5673b427a1Fa98AFc48FfDE7Ba43"},
            "deploy": {
                "contract": "0xa3d9Fbd0edB10327ECB73D2C72622E505dF468a2",
                "amount": 0.000035  # Manual success value
            }
        }
        self.REFERRER = "0x0000000000000000000000000000000000000000"
        
        self.CONTRACT_ABI = [
            {"type":"function","name":"timeUntilNextGM","stateMutability":"view","inputs":[{"name":"user","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"GM_FEE","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"onChainGM","stateMutability":"payable","inputs":[{"name":"referrer","type":"address"}],"outputs":[]},
            {"type":"function","name":"deploy","stateMutability":"payable","inputs":[],"outputs":[]}
        ]
        self.deploy_count = 0

    def log(self, message):
        print(f"{Fore.CYAN}[{datetime.now().astimezone(wib).strftime('%H:%M:%S')}]{Style.RESET_ALL} | {message}", flush=True)

    async def submit_tx(self, endpoint, address, tx_hash):
        url = f"{self.BASE_API}/{endpoint}"
        headers = {
            "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpldnp5enVwY2F6cmFpZGZ1ZWduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQxMzEwNzEsImV4cCI6MjA2OTcwNzA3MX0.FOoTuTzLq8Wg62fKHiBzRM7cPG3NgR8yrxbsOAvrW6k",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpldnp5enVwY2F6cmFpZGZ1ZWduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQxMzEwNzEsImV4cCI6MjA2OTcwNzA3MX0.FOoTuTzLq8Wg62fKHiBzRM7cPG3NgR8yrxbsOAvrW6k",
            "Content-Type": "application/json"
        }
        payload = {"user_address": address, "network_id": self.ARC_NETWORK["network_id"], "network_name": self.ARC_NETWORK["network_name"], "transaction_hash": tx_hash}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status in [200, 201]: self.log(f"{Fore.GREEN}API Status: Submitted to {endpoint}")
        except: pass

    async def perform_gm(self, account_key, address, web3):
        try:
            contract = web3.eth.contract(address=web3.to_checksum_address(self.ARC_NETWORK["onchain_gm"]["contract"]), abi=self.CONTRACT_ABI)
            wait_time = contract.functions.timeUntilNextGM(address).call()
            if wait_time > 0:
                self.log(f"{Fore.YELLOW}GM Cooldown: {wait_time}s")
                return None

            fee = contract.functions.GM_FEE().call()
            tx = contract.functions.onChainGM(web3.to_checksum_address(self.REFERRER)).build_transaction({
                "from": address, "value": fee, "nonce": web3.eth.get_transaction_count(address),
                "gas": 300000, "gasPrice": int(web3.eth.gas_price * 1.1), "chainId": self.ARC_NETWORK["network_id"]
            })
            signed = web3.eth.account.sign_transaction(tx, account_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed.raw_transaction))
            self.log(f"GM Tx Sent: {tx_hash}")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                await self.submit_tx("gm_transactions", address, tx_hash)
                return tx_hash
            return None
        except Exception as e:
            self.log(f"{Fore.RED}GM Error: {e}")
            return None

    async def perform_deploy(self, account_key, address, web3):
        try:
            contract_addr = web3.to_checksum_address(self.ARC_NETWORK["deploy"]["contract"])
            contract = web3.eth.contract(address=contract_addr, abi=self.CONTRACT_ABI)
            value = web3.to_wei(self.ARC_NETWORK["deploy"]["amount"], 'ether')
            
            tx = contract.functions.deploy().build_transaction({
                "from": address, "value": value, "nonce": web3.eth.get_transaction_count(address),
                "gas": 300000, "gasPrice": int(web3.eth.gas_price * 1.1), "chainId": self.ARC_NETWORK["network_id"]
            })
            signed = web3.eth.account.sign_transaction(tx, account_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed.raw_transaction))
            self.log(f"Deploy Tx Sent: {tx_hash}")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                await self.submit_tx("deploy_transactions", address, tx_hash)
                return tx_hash
            return None
        except Exception as e:
            self.log(f"{Fore.RED}Deploy Error: {e}")
            return None

    def print_question(self):
        print(f"{Fore.GREEN}1. Onchain GM\n2. Deploy Contract\n3. Run All Features")
        option = int(input(f"{Fore.BLUE}Choose [1/2/3] -> ").strip())
        if option in [2, 3]:
            self.deploy_count = int(input(f"{Fore.YELLOW}Enter Deploy Count per account -> ").strip())
        return option

    async def main(self):
        if not os.path.exists('accounts.txt'): return
        with open('accounts.txt', 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]
        
        option = self.print_question()
        web3 = Web3(Web3.HTTPProvider(self.ARC_NETWORK["rpc_url"]))

        while True:
            self.log(f"Total Accounts: {len(accounts)}")
            for acc in accounts:
                address = Account.from_key(acc).address
                self.log(f"--- Processing: {address[:10]}... ---")
                
                if option in [1, 3]:
                    await self.perform_gm(acc, address, web3)
                
                if option in [2, 3]:
                    for i in range(self.deploy_count):
                        self.log(f"Deploying {i+1}/{self.deploy_count}")
                        await self.perform_deploy(acc, address, web3)
                        await asyncio.sleep(2)
                
                await asyncio.sleep(3)
            
            self.log("All accounts processed. Sleeping for 24 hours...")
            await asyncio.sleep(24 * 3600)

if __name__ == "__main__":
    asyncio.run(GM().main())
