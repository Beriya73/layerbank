import asyncio
import logging
from client import Client
from config import LAYERBANK_CONTRACTS, LAYERBANK_lUSDC, LAYERBANK_CORE, TOKENS_PER_CHAIN
from functions import get_amount
from termcolor import colored

# Настройка логирования
file_log = logging.FileHandler('file.log')
console_out = logging.StreamHandler()
logging.basicConfig(handlers=(file_log, console_out),
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

class LayerBank:
    """
    Класс LayerBank для взаимодействия с контрактами LayerBank.

    Attributes:
        client (Client): Клиент для взаимодействия с блокчейном.
        token_contract: Контракт токена USDC.
        core_contract: Основной контракт LayerBank.
    """

    def __init__(self, client: Client):
        """
        Инициализация класса LayerBank.

        Args:
            client (Client): Клиент для взаимодействия с блокчейном.
        """
        self.client = client
        # Получаем контракт USDC токена
        self.token_contract = self.client.get_contract(
            contract_address=LAYERBANK_CONTRACTS[self.client.chain_name]['USDC'], abi=LAYERBANK_lUSDC
        )
        # Получаем основной контракт LayerBank
        self.core_contract = self.client.get_contract(
            contract_address=LAYERBANK_CONTRACTS[self.client.chain_name]['Core'],
            abi=LAYERBANK_CORE,
        )

    async def supply(self, amount_in_wei: float):
        """
        Внесение средств в контракт LayerBank.

        Args:
            amount_in_wei (float): Сумма в wei для внесения в контракт.

        Returns:
            dict: Результат отправки транзакции.
        """
        # Выполнение одобрения (approve) токенов для контракта
        await self.client.make_approve(
            TOKENS_PER_CHAIN[self.client.chain_name][self.client.chain_token], self.token_contract.address, 2 ** 256 - 1
        )
        # Создание транзакции для внесения средств
        transaction = await self.core_contract.functions.supply(
            LAYERBANK_CONTRACTS[self.client.chain_name]['USDC'],
            amount_in_wei,
        ).build_transaction(await self.client.prepare_tx(value=amount_in_wei))

        # Отправка транзакции
        return await self.client.send_transaction(transaction)

    async def winthdraw(self):
        """
        Вывод средств из контракта LayerBank.

        Returns:
            dict: Результат отправки транзакции.
        """
        # Получение баланса токенов на адресе клиента
        amount_in_wei = await self.token_contract.functions.balanceOf(self.client.address).call()
        # Создание транзакции для вывода средств
        transaction = await self.core_contract.functions.redeemToken(
            LAYERBANK_CONTRACTS[self.client.chain_name]['USDC'],
            amount_in_wei,
        ).build_transaction(await self.client.prepare_tx())

        # Отправка транзакции
        return await self.client.send_transaction(transaction)

async def main():
    """
    Основная функция для взаимодействия с пользователем и контрактом LayerBank.
    """
    proxy = ''
    # Получение private_key от пользователя
    while True:
        try:
            private_key = input(colored("Введите private key: ", 'light_green'))
            w3_client = Client(private_key=private_key, proxy=proxy)
            break
        except Exception as er:
            logging.error(f"Некорректный private key! {er}")

    layer_client = LayerBank(client=w3_client)
    try:
        # Получение баланса USDC токенов
        balance = await layer_client.client.get_balance(TOKENS_PER_CHAIN['Scroll']['USDC'])
    except Exception as er:
        logging.error(f"Ошибка при получении баланса: {er}")
        exit(1)

    # Преобразование баланса в wei
    amount_in_wei = get_amount(balance)
    logging.info("Пробуем аппрувить и положить в лендинг")
    try:
        # Попытка внесения средств в лендинг
        await layer_client.supply(amount_in_wei)
        logging.info("Удачно!")
    except Exception as er:
        logging.error(f"Ошибка при лендинге!")
        exit(1)

    # Вопрос пользователю о выводе средств
    response = input(colored("Вывести из пула?", 'light_green'))
    try:
        if response in "YyДд":
            logging.info(f"Выводим из пула USDC")
            # Попытка вывода средств
            await layer_client.winthdraw()
            logging.info("Удачно!")
        else:
            logging.info("Программа завершилась")
    except Exception as er:
        logging.info(f"Ошибка вывода из пула",)

# Запуск основной функции
asyncio.run(main())
