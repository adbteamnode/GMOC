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
            "onchain_gm": {"contract": "0x363cC75a89aE5673b427a1Fa98AFc48FfDE7Ba43"}
        }
        self.REFERRER = "0xc2fcFd1bF7CB2Cdd14A9B0dADB4FdcB845219D01"
        self.CONTRACT_ABI = [
            {"type":"function","name":"timeUntilNextGM","stateMutability":"view","inputs":[{"name":"user","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"onChainGM","stateMutability":"payable","inputs":[{"name":"referrer","type":"address"}],"outputs":[]}
        ]

    def log(self, message):
        print(f"{Fore.CYAN}[{datetime.now().astimezone(wib).strftime('%H:%M:%S')}]{Style.RESET_ALL} | {message}", flush=True)

    async def submit_to_api(self, address, tx_hash):
        # This part registers your points on the Onchain GM website
        url = f"{self.BASE_API}/gm_transactions"
        headers = {
            "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpldnp5enVwY2F6cmFpZGZ1ZWduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQxMzEwNzEsImV4cCI6MjA2OTcwNzA3MX0.FOoTuTzLq8Wg62fKHiBzRM7cPG3NgR8yrxbsOAvrW6k",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpldnp5enVwY2F6cmFpZGZ1ZWduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQxMzEwNzEsImV4cCI6MjA2OTcwNzA3MX0.FOoTuTzLq8Wg62fKHiBzRM7cPG3NgR8yrxbsOAvrW6k",
            "Content-Type": "application/json"
        }
        payload = {
            "user_address": address,
            "network_id": self.ARC_NETWORK["network_id"],
            "network_name": self.ARC_NETWORK["network_name"],
            "transaction_hash": tx_hash
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status in [200, 201]:
                        self.log(f"{Fore.GREEN}API Status: Points Registered Successfully")
        except: pass

    async def perform_gm(self, account_key, address):
        try:
            web3 = Web3(Web3.HTTPProvider(self.ARC_NETWORK["rpc_url"]))
            contract = web3.eth.contract(address=web3.to_checksum_address(self.ARC_NETWORK["onchain_gm"]["contract"]), abi=self.CONTRACT_ABI)
            
            wait_time = contract.functions.timeUntilNextGM(address).call()
            if wait_time > 0:
                self.log(f"{Fore.YELLOW}Cooldown active: {wait_time}s")
                return None

            # CORRECTED FEE: 0.05 USDC
            fee = web3.to_wei(0.05, 'ether') 
            nonce = web3.eth.get_transaction_count(address)
            
            gm_tx = contract.functions.onChainGM(web3.to_checksum_address(self.REFERRER)).build_transaction({
                "from": address, "value": fee, "nonce": nonce, "gas": 350000,
                "gasPrice": int(web3.eth.gas_price * 1.1), "chainId": self.ARC_NETWORK["network_id"]
            })
            
            signed = web3.eth.account.sign_transaction(gm_tx, account_key)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            hex_hash = web3.to_hex(tx_hash)
            self.log(f"Tx Sent: {hex_hash}")
            
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                await self.submit_to_api(address, hex_hash)
                return hex_hash, receipt.blockNumber
            else:
                self.log(f"{Fore.RED}Reverted. Ensure you have exactly 0.05 USDC for fee.")
                return None
        except Exception as e:
            self.log(f"{Fore.RED}Error: {e}")
            return None

    async def main(self):
        if not os.path.exists('accounts.txt'): return
        with open('accounts.txt', 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]

        for acc in accounts:
            address = Account.from_key(acc).address
            self.log(f"--- Account: {address[:8]}... ---")
            res = await self.perform_gm(acc, address)
            if res: self.log(f"{Fore.GREEN}GM SUCCESS!")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(GM().main())
