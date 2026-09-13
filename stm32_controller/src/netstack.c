#include <stddef.h>
#include "netstack.h"
#include "uart.h"


/* Public functions ----------------------------------------------------------*/
netstack_status_e netstack_build_packet(uint8_t is_rx,
	uint8_t type, const uint8_t params[static 2], packet_t* pkt) {
	if ((pkt == NULL) || (params == NULL)) {
	if (pkt == NULL || params == NULL) {
		return NETSTACK_STATUS_ERROR;
	}

	pkt->link_header.sof = NETSTACK_SOF;
	pkt->link_header.is_rx = is_rx;
	pkt->type = type;
	pkt->params[0] = params[0];
	pkt->params[1] = params[1];

	return NETSTACK_STATUS_OK;
}

netstack_status_e netstack_breakdown_packet(const packet_t* pkt,
	uint8_t* is_rx,	uint8_t* type, uint8_t params[static 2]) {
	if ((pkt == NULL) || (is_rx == NULL) || (type == NULL)
		|| (params == NULL)) {
	if (pkt == NULL || type == NULL || params == NULL) {
		return NETSTACK_STATUS_ERROR;
	}

	*is_rx = pkt->link_header.is_rx;
	*type = pkt->type;
	params[0] = pkt->params[0];
	params[1] = pkt->params[1];

	return NETSTACK_STATUS_OK;
}