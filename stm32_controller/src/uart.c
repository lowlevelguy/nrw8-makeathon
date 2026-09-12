#include "uart.h"

#include "stm32f4xx_hal.h"


/* Private variables ----------------------------------------------------------*/
volatile uint8_t uart_xfer_done = 1, uart_xfer_ok = 1;


/* Public variables ----------------------------------------------------------*/
UART_HandleTypeDef huart2;


/* External functions --------------------------------------------------------*/
extern void Error_Handler(void);

void HAL_UART_TxCpltCallback(UART_HandleTypeDef* huart) {
	if (huart->Instance == huart2.Instance) {
		uart_xfer_done = 1;
	}
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef* huart) {
	if (huart->Instance == huart2.Instance) {
		uart_xfer_done = 1;
	}
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart) {
	if (huart->Instance == huart2.Instance) {
		uart_xfer_done = 1;
		uart_xfer_ok = 0;
	}
}


/* Public functions ----------------------------------------------------------*/
void uart_init() {
	huart2.Instance = USART2;
	huart2.Init.BaudRate = 115200;
	huart2.Init.WordLength = UART_WORDLENGTH_8B;
	huart2.Init.StopBits = UART_STOPBITS_1;
	huart2.Init.Parity = UART_PARITY_NONE;
	huart2.Init.Mode = UART_MODE_TX_RX;
	huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
	huart2.Init.OverSampling = UART_OVERSAMPLING_16;
	if (HAL_UART_Init(&huart2) != HAL_OK) {
		Error_Handler();
	}
}

uart_status_e uart_tx(uint8_t* buf, uint16_t buf_size) {
	if (uart_xfer_done == 0) {
		return UART_STATUS_BUSY;
	}

	uart_xfer_done = 0;
	if (HAL_UART_Transmit_DMA(&huart2, buf, buf_size) != HAL_OK) {
		return UART_STATUS_HAL_ERROR;
	}

	while (uart_xfer_done == 0) {
		HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
	}

	return UART_STATUS_OK;
}

uart_status_e uart_rx(uint8_t* buf, uint16_t buf_size) {
	if (uart_xfer_done == 0) {
		return UART_STATUS_BUSY;
	}

	uart_xfer_done = 0;
	if (HAL_UART_Receive_DMA(&huart2, buf, buf_size) != HAL_OK) {
		return UART_STATUS_HAL_ERROR;
	}

	while (uart_xfer_done == 0) {
		HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
	}

	return UART_STATUS_OK;
}
