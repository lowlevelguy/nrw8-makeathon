#ifndef NETSTACK_H_
#define NETSTACK_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>


#define NETSTACK_SOF	(0xAAu & 0xFE)


/* Types ---------------------------------------------------------------------*/
typedef enum {
	NETSTACK_STATUS_OK,
	NETSTACK_STATUS_ERROR,
} netstack_status_e;

/**
 * TX packet application layer types
 */
enum {
	TX_PACKET_SELECT_INPUT_LANE,
	TX_PACKET_SELECT_OUTPUT_LANE,
	TX_PACKET_KERNELS_ACK,
	TX_PACKET_KERNELS_NACK,
	TX_PACKET_FETCH_COMPLETE,
	TX_PACKET_SELECT_OUTPUT_LANE_AND_RESTOCK,
};

/**
 * RX packet application layer types
 */
enum {
	RX_PACKET_BARCODE_READING,
	RX_PACKET_FETCH_KERNELS_REQUEST,
	RX_PACKET_BOX_FETCH_DONE
};

typedef struct {
	uint8_t sof : 7,
			is_rx : 1;
} link_header_t;

typedef struct {
	link_header_t link_header;

	// Application layer
	union {
		uint8_t payload[3];
		struct {
			uint8_t type, params[2];
		};
	};
} packet_t;


/* Public functions ----------------------------------------------------------*/
/**
 * @brief Builds a packet given a 3-byte payload and information on whether it
 * is for TX or RX.
 *
 * @param is_rx [in] boolean; 0 = TX packet, 1 = RX packet
 * @param is_rx [in] boolean; 0 = RX packet desired, 1 = TX packet desired
 * @param type [in] contains the application layer type
 * @param params [in] 2-byte buffer containing the application layer parameters
 * @param pkt [out] pointer to packet_t object that will contain the final
 * packet
 *
 * @return NETSTACK_STATUS_OK if no errors are there, NETSTACK_STATUS_ERROR if
 * either of pkt or payload is NULL
 *
 * @note The contents of payload are copied to pkt's internal buffer, rather
 * than a pointer assignment being used.
 */
netstack_status_e netstack_build_packet(uint8_t is_rx, uint8_t type,
	const uint8_t params[static 2], packet_t* pkt);

/**
 *
 * @param pkt [in] pointer to the packet to be broken down
 * @param is_rx[out] pointer to boolean that will contain whether the packet
 * is RX (value of 1) or TX (value of 0)
 * @param type [out] pointer to byte that will contain the extracted application
 * layer type
 * @param params [out] 2-byte buffer that will contain the extracted application
 * layer parameters
 *
 * @return NETSTACK_STATUS_OK if no errors are there, NETSTACK_STATUS_ERROR if
 * either of pkt or payload is NULL
 */
netstack_status_e netstack_breakdown_packet(const packet_t* pkt,
	uint8_t* is_rx,	uint8_t* type, uint8_t params[static 2]);


#ifdef __cplusplus
}
#endif

#endif /* NETSTACK_H_ */