#ifndef UART_H_
#define UART_H_

#ifdef __cplusplus
extern "C" {
#endif


#include <stdint.h>


/* Types ---------------------------------------------------------------------*/
typedef enum {
	UART_STATUS_OK,
	UART_STATUS_BUSY,
	UART_STATUS_HAL_ERROR
} uart_status_e;


/* Public functions-----------------------------------------------------------*/
/**
 * @brief Initialises UART peripheral interface.
 *
 * @note Uses USART2.
 */
void uart_init();

/**
 * @brief Initiates UART TX transfer, and blocks invoking thread until
 * completion.
 *
 * @note Uses DMA.
 *
 * @param buf buffer containing the data to transfer
 * @param buf_size size in bytes of buf
 * @return UART_STATUS_OK in case of success, UART_STATUS_BUSY if UART is busy,
 * and UART_STATUS_HAL_ERROR otherwise.
 */
uart_status_e uart_tx(uint8_t* buf, uint16_t buf_size);

/**
 * @brief Initiates UART RX, and blocks invoking thread until completion.
 *
 * @note Uses DMA.
 *
 * @param buf buffer to receive incoming data into
 * @param buf_size size in bytes of the expected data
 * @return UART_STATUS_OK in case of success, UART_STATUS_BUSY if UART is busy,
 * and UART_STATUS_HAL_ERROR otherwise.
 */
uart_status_e uart_rx(uint8_t* buf, uint16_t buf_size);


#ifdef __cplusplus
}
#endif

#endif /* UART_H_ */