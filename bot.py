from web3 import Web3
from eth_account import Account
from datetime import datetime
from dotenv import load_dotenv
from colorama import *
import asyncio, os, pytz, time

load_dotenv()

# Set Timezone
wib = pytz.timezone('Asia/Jakarta')

class GM:
    def __init__(self) -> None:
        # Arc Testnet Configuration
        self.ARC_NETWORK = {
            "network_name": "Arc Testnet",
            "ticker": "USDC",
            "rpc_url": "https://rpc.testnet.arc.network",
            "explorer": "https://testnet.arcscan.app/tx/",
            "network_id": 5042002,
            "onchain_gm": {
                "contract": "0x363cC75a89aE5673b427a1Fa98AFc48FfDE7Ba43"
            }
        }
        
        # Your specific referrer address
        self.REFERRER = "0xc2fcFd1bF7CB2Cdd14A9B0dADB4FdcB845219D01"
        
        # Minimized ABI for GM features
        self.CONTRACT_ABI = [
            {
                "type": "function", 
                "name": "timeUntilNextGM", 
                "stateMutability": "view", 
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}], 
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}]
            },
            {
                "type": "function", 
                "name": "onChainGM", 
                "stateMutability": "payable", 
                "inputs": [{"internalType": "address", "name": "referrer", "type": "address"}], 
                "outputs": []
            }
        ]

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%H:%M:%S')} ]{Style.RESET_ALL}"
            f" | {message}", 
            flush=True
        )

    def welcome(self):
        print(f"{Fore.GREEN + Style.BRIGHT}Arc Testnet {Fore.BLUE + Style.BRIGHT}Auto GM BOT")
        print(f"{Fore.WHITE}Referrer: {self.REFERRER}{Style.RESET_ALL}\n")

    async def perform_gm(self, account_key, address):
        try:
            web3 = Web3(Web3.HTTPProvider(self.ARC_NETWORK["rpc_url"]))
            
            # Connection Check
            if not web3.is_connected():
                self.log(f"{Fore.RED}RPC Connection Failed")
                return None

            contract_addr = web3.to_checksum_address(self.ARC_NETWORK["onchain_gm"]["contract"])
            contract = web3.eth.contract(address=contract_addr, abi=self.CONTRACT_ABI)
            
            # 1. Check Cool-down Status
            self.log("Checking cool-down status...")
            wait_time = contract.functions.timeUntilNextGM(address).call()
            
            if wait_time > 0:
                self.log(f"{Fore.YELLOW}In cool-down. Remaining: {wait_time}s")
                return None

            # 2. Setup Transaction Parameters
            # Using 0.5 USDC as requested
            fee = web3.to_wei(0.5, 'ether') 
            nonce = web3.eth.get_transaction_count(address)
            gas_price = int(web3.eth.gas_price * 1.2) # 20% Tip for faster inclusion
            
            self.log(f"Preparing GM with 0.5 {self.ARC_NETWORK['ticker']} fee...")

            # 3. Build Transaction (Fixed Gas to bypass local revert check)
            gm_tx = contract.functions.onChainGM(
                web3.to_checksum_address(self.REFERRER)
            ).build_transaction({
                "from": address,
                "value": fee,
                "nonce": nonce,
                "gas": 400000, # Increased Fixed Gas Limit
                "gasPrice": gas_price,
                "chainId": self.ARC_NETWORK["network_id"]
            })
            
            # 4. Sign and Broadcast
            signed = web3.eth.account.sign_transaction(gm_tx, account_key)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            
            hex_hash = web3.to_hex(tx_hash)
            self.log(f"Tx Sent: {hex_hash}")
            self.log("Waiting for confirmation on-chain...")
            
            # Wait for receipt
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt.status == 1:
                return hex_hash, receipt.blockNumber
            else:
                self.log(f"{Fore.RED}Transaction REVERTED on-chain. Check explorer link below.")
                self.log(f"Link: {self.ARC_NETWORK['explorer']}{hex_hash}")
                return None
                
        except Exception as e:
            self.log(f"{Fore.RED}Error: {str(e)}")
            return None

    async def main(self):
        self.clear_terminal()
        self.welcome()

        if not os.path.exists('accounts.txt'):
            self.log(f"{Fore.RED}File 'accounts.txt' not found!")
            return
            
        with open('accounts.txt', 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]

        self.log(f"Total Accounts loaded: {len(accounts)}")
        print("-" * 50)

        for acc in accounts:
            try:
                address = Account.from_key(acc).address
                self.log(f"Processing: {Fore.WHITE}{address[:8]}...{address[-8:]}{Style.RESET_ALL}")
                
                # Check Balance
                web3 = Web3(Web3.HTTPProvider(self.ARC_NETWORK["rpc_url"]))
                balance = web3.from_wei(web3.eth.get_balance(address), 'ether')
                self.log(f"Current Balance: {balance} {self.ARC_NETWORK['ticker']}")

                if balance < 0.5:
                    self.log(f"{Fore.RED}Balance too low (< 0.5). Skipping...")
                    continue

                result = await self.perform_gm(acc, address)
                if result:
                    tx, block = result
                    self.log(f"{Fore.GREEN}SUCCESS! Confirmed in Block: {block}")
                    self.log(f"Explorer: {self.ARC_NETWORK['explorer']}{tx}")
                
                print("-" * 50)
                await asyncio.sleep(3) # Short delay between accounts

            except Exception as e:
                self.log(f"{Fore.RED}Critical Account Error: {e}")

        self.log(f"{Fore.BLUE}All tasks completed. Finished.")

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    bot = GM()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot stopped by user.")
