#ifndef NETSTACK_H_
#define NETSTACK_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

typedef enum {
	NETSTACK_STATUS_OK,
	NETSTACK_STATUS_NULL_ERROR,
	NETSTACK_STATUS_INVALID_PAYLOAD
} netstack_status_e;

typedef enum {
	PACKET_TYPE_RX_BOX_METADATA_READING,
	PACKET_TYPE_RX_KERNELS_QUERY,
	PACKET_TYPE_RX_COUNT,

	PACKET_TYPE_TX_INPUT_RAIL_SELECT,
	PACKET_TYPE_TX_OUTPUT_RAIL_SELECT,

	PACKET_TYPE_COUNT
} packet_type_e;

typedef struct {
	uint8_t sof;
	packet_type_e type;
} link_header_t;

typedef struct {
	link_header_t link_header;
	uint8_t payload[2];
} packet_t;


packet_t netstack_build_packet(packet_type_e type, uint8_t payload[2]);
netstack_status_e netstack_handle_rx(packet_t* pkt);


#ifdef __cplusplus
}
#endif

#endif /* NETSTACK_H_ */