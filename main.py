import asyncio
import json
import random
import csv
from typing import List, Dict, Optional
from exchanges.mexc import MexcWithdraw
from exchanges.binance import BinanceWithdraw
from exchanges.okx import OkxWithdraw
from exchanges.bitget import BitgetWithdraw
from exchanges.gate import GateWithdraw
import platform
import psutil
from datetime import datetime
import time

def load_addresses() -> List[Dict]:
    """从CSV文件加载地址和参数"""
    try:
        addresses = []
        with open('add.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                addresses.append({
                    'address': row['add'].strip(),
                    'memo': row.get('memo', '').strip(),
                    'id': row.get('id', '').strip(),
                    'remark': row.get('remark', '').strip()
                })
        print(f'成功加载 {len(addresses)} 个地址')
        return addresses
    except Exception as e:
        print(f'加载地址文件失败: {str(e)}')
        exit(1)

def load_config() -> Dict:
    """加载配置文件"""
    try:
        with open('config.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f'加载配置文件失败: {str(e)}')
        exit(1)

async def get_withdraw_config(exchange_instance) -> Dict:
    """获取提币通用配置"""
    print("\n" + "─" * 40)
    print("📝 提币参数配置")
    print("─" * 40)
    
    config = {}

    # 输入币种
    config['coin'] = input("\n💱 请输入币种 (例如: ETH): ").upper()
    
    # 获取并显示该币种支持的网络
    try:
        coin_list = exchange_instance.get_coinlist()
        networks = []
        for coin_info in coin_list:
            if coin_info['coin'].upper() == config['coin']:
                if 'networkList' in coin_info:
                    networks = [network['network'] for network in coin_info['networkList']]
                break
        
        if networks:
            print(f"\n🌐 {config['coin']} 支持的网络:")
            for i, network in enumerate(networks, 1):
                print(f"{i}. {network}")
            
            # 输入网络选择
            while True:
                try:
                    choice = int(input("\n🔢 请选择网络编号: "))
                    if 1 <= choice <= len(networks):
                        config['network'] = networks[choice-1]
                        break
                    else:
                        print("❌ 无效的选择，请重新输入")
                except ValueError:
                    print("❌ 请输入有效的数字")
        else:
            raise Exception(f"❌ 币种 {config['coin']} 不存在或不支持提币")

    except Exception as e:
        raise Exception(f"❌ 获取网络信息失败: {str(e)}")
    
    # 金额设置
    amount_input = input("\n💰 请输入提币数量 (可以输入范围/也可固定，如: 1-10/1): ")
    if '-' in amount_input:
        min_amount, max_amount = map(float, amount_input.split('-'))
        config['amount'] = {'min': min_amount, 'max': max_amount}
    else:
        config['amount'] = float(amount_input)

    # 时间间隔设置
    interval_input = input("⏱️  请输入间隔时间(秒) (可以输入范围/也可固定，如: 30-90/100): ")
    if '-' in interval_input:
        min_interval, max_interval = map(float, interval_input.split('-'))
        config['timeInterval'] = {'min': min_interval, 'max': max_interval}
    else:
        interval = float(interval_input)
        config['timeInterval'] = {'min': interval, 'max': interval}

    print("\n✅ 配置完成!")
    return config


def get_exchange_credentials(exchange: str, config: Dict) -> Dict:
    """获取交易所凭证"""
    credentials = {}
    
    if exchange == '1':  # MEXC
        if not config.get('mexc', {}).get('api_key') or not config.get('mexc', {}).get('api_secret'):
            raise ValueError('MEXC API 配置不完整')
        credentials = {
            'api_key': config['mexc']['api_key'],
            'api_secret': config['mexc']['api_secret']
        }
    elif exchange == '2':  # Binance
        if not config.get('binance', {}).get('api_key') or not config.get('binance', {}).get('api_secret'):
            raise ValueError('Binance API 配置不完整')
        credentials = {
            'api_key': config['binance']['api_key'],
            'api_secret': config['binance']['api_secret']
        }
    elif exchange == '3':  # OKX
        if not config.get('okx', {}).get('api_key') or not config.get('okx', {}).get('api_secret') or not config.get('okx', {}).get('password'):
            raise ValueError('OKX API 配置不完整')
        credentials = {
            'api_key': config['okx']['api_key'],
            'api_secret': config['okx']['api_secret'],
            'password': config['okx']['password']
        }
    elif exchange == '4':  # Bitget
        if not config.get('bitget', {}).get('api_key') or not config.get('bitget', {}).get('api_secret') or not config.get('bitget', {}).get('password'):
            raise ValueError('Bitget API 配置不完整')
        credentials = {
            'api_key': config['bitget']['api_key'],
            'api_secret': config['bitget']['api_secret'],
            'password': config['bitget']['password']
        }
    elif exchange == '5':  # Gate
        if not config.get('gate', {}).get('api_key') or not config.get('gate', {}).get('api_secret'):
            raise ValueError('Gate API 配置不完整')
        credentials = {
            'api_key': config['gate']['api_key'],
            'api_secret': config['gate']['api_secret']
        }
    
    return credentials

async def process_withdrawals(exchange_instance, addresses: List[Dict], withdraw_config: Dict):
    """通用提币处理流程"""
    total = len(addresses)
    print(f"\n" + "─" * 40)
    print(f"📋 总计待处理地址: {total}")
    print("─" * 40)
    
    for i, addr_info in enumerate(addresses, 1):
        print(f"\n🔄 进度: {i}/{total}")
        print(f"📬 提币地址: {addr_info['address']}")

        # 计算提币金额
        if isinstance(withdraw_config['amount'], dict):
            amount = random.uniform(
                withdraw_config['amount']['min'],
                withdraw_config['amount']['max']
            )
        else:
            amount = withdraw_config['amount']

        # 执行提币
        try:
            print(f"💰 提币金额: {amount} {withdraw_config['coin']}")
            result = await exchange_instance.withdraw(
                coin=withdraw_config['coin'],
                network=withdraw_config['network'],
                address=addr_info['address'],
                amount=str(amount),
                memo=addr_info['memo'],
                withdraw_order_id=addr_info['id'],
                remark=addr_info['remark']
            )
            print(f"✅ 提币成功: {result}")

        except Exception as e:
            print(f"❌ 提币失败: {str(e)}")
            continue

        # 如果不是最后一个地址，则等待
        if i < len(addresses):
            wait_time = random.uniform(
                withdraw_config['timeInterval']['min'],
                withdraw_config['timeInterval']['max']
            )
            print(f"⏳ 等待 {wait_time:.2f} 秒后继续...")
            await asyncio.sleep(wait_time)

async def select_exchange() -> bool:
    """选择交易所"""
    print("\n" + "=" * 34)
    print("           Bbot提币工具")
    print("=" * 34)
    print("\n请选择要使用的交易所:")
    print("┌────────────────────────────────┐")
    print("│  1. MEXC    - 抹茶             │")
    print("│  2. Binance - 币安             │")
    print("│  3. OKX     - 欧易             │")
    print("│  4. Bitget  - 比特             │")
    print("│  5. Gate    - 芝麻             │")
    print("│  0. Exit    - 退出程序         │")
    print("└────────────────────────────────┘")

    answer = input('请输入选项数字: ')
    
    if answer == '0':
        print('\n感谢使用 Bbot 提币工具!')
        print('正在安全退出...')
        return False

    try:
        # 加载配置
        addresses = load_addresses()
        config = load_config()
        credentials = get_exchange_credentials(answer, config)

        # 根据选择创建相应的交易所实例并执行提币
        if answer == '1':
            print('\n【MEXC】抹茶交易所 - 开始提币流程')
            mexc = MexcWithdraw(credentials)
            withdraw_config = await get_withdraw_config(mexc)
            await process_withdrawals(mexc, addresses, withdraw_config)
        
        elif answer == '2':
            print('\n【Binance】币安交易所 - 开始提币流程')
            binance = BinanceWithdraw(credentials)
            withdraw_config = await get_withdraw_config(binance)
            await process_withdrawals(binance, addresses, withdraw_config)
        
        elif answer == '3':
            print('\n【OKX】欧易交易所 - 开始提币流程')
            print('注意: 请确保已添加提币地址白名单')
            okx = OkxWithdraw(credentials)
            withdraw_config = await get_withdraw_config(okx)
            await process_withdrawals(okx, addresses, withdraw_config)
        
        elif answer == '4':
            print('\n【Bitget】比特交易所 - 开始提币流程')
            bitget = BitgetWithdraw(credentials)
            withdraw_config = await get_withdraw_config(bitget)
            await process_withdrawals(bitget, addresses, withdraw_config)
        
        elif answer == '5':
            print('\n【Gate】芝麻交易所 - 开始提币流程')
            gate = GateWithdraw(credentials)
            withdraw_config = await get_withdraw_config(gate)
            await process_withdrawals(gate, addresses, withdraw_config)
        
        else:
            print('\n❌ 无效选项，请重新选择')
            return True

    except Exception as e:
        print(f'\n❌ 操作失败: {str(e)}')
        return True

    return True

def print_startup_info():
    """打印启动信息和交易所邀请链接"""
    # 清屏
    print('\033[2J\033[H')
    
    # ASCII art logo
    logo = """
    ╔═══════════════════════════════════════════════╗
    ║   ____  _           _                         ║
    ║  | __ )| |__   ___ | |_                       ║
    ║  |  _ \| '_ \ / _ \| __|                      ║
    ║  | |_) | |_ ) | (_) | |_                      ║
    ║  |____/|_.__/ \___/ \__|                      ║
    ║                                               ║
    ║         Bbot - 多链批量提币机器人             ║
    ║                           v1.0.0              ║
    ╚═══════════════════════════════════════════════╝
    """
    print(logo)
    
    # 交易所邀请链接
    exchange_links = """
    🔗 交易所邀请链接:
    ┌────────────────────────────────────────────────────────────────────────────────────────────┐
    │ 1. MEXC 抹茶                                                                               │
    │    • 注册链接: https://promote.mexc.com/r/TS5B9iU1                                         │
    │                                                                                            │
    │ 2. Binance 币安                                                                            │
    │    • 注册链接: https://www.marketwebb.blue/activity/referral-entry/CPA?ref=CPA_00K7K6TXL5  │
    │                                                                                            │
    │ 3. OKX 欧易                                                                                │
    │    • 注册链接: https://chouyi.pro/join/60393336                                            │
    │                                                                                            │
    │ 4. Bitget 比特                                                                             │
    │    • 注册链接: https://share.glassgs.com/u/DYT7NWH4                                        │
    │                                                                                            │
    │ 5. Gate.io 芝麻                                                                            │
    │    • 注册链接: https://www.gt-io.best/signup/BARMA1sO?ref_type=103                         │
    │                                                                                            │    
    │ 6. Bybit U卡注册                                                                           │
    │    • 注册链接: https://www.bybit.com/invite?ref=VLOJ1Y                                     │
    └────────────────────────────────────────────────────────────────────────────────────────────┘
    """
    print(exchange_links)
    
    # 重要提示
    important_notice = """
    ⚠️ 重要提示:
    1. 请确保您的API密钥已正确配置
    2. 建议先使用小额测试提币功能
    3. 部分交易所要求提币地址必须先在网页端验证
    4. 请确保提币地址正确，且支持选择的网络
    """
    print(important_notice)
    
    input("\n按回车键继续...")

async def main():
    """主函数"""
    try:
        # 添加启动界面
        print_startup_info()
        
        continue_running = True
        while continue_running:
            continue_running = await select_exchange()
    except Exception as e:
        print(f'程序执行错误: {str(e)}')

if __name__ == "__main__":
    asyncio.run(main())