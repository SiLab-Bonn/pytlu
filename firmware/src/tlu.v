/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University 
 * ------------------------------------------------------------
 */

`include "utils/reset_gen.v"
`include "utils/bus_to_ip.v"
`include "utils/clock_divider.v"

`include "gpio/gpio.v"

`include "i2c/i2c.v"
`include "i2c/i2c_core.v"
`include "utils/cdc_pulse_sync.v"

`ifdef COCOTB_SIM //for simulation
    `include "utils/BUFG_sim.v" 
`else

`endif

module tlu (
        input wire BUS_CLK_IN,
        input wire [15:0] USB_BUS_ADD,
        inout wire [7:0] BUS_DATA,
        input wire BUS_OE_N,
        input wire BUS_RD_N,
        input wire BUS_WR_N,
        input wire BUS_CS_N,

        input wire USB_STREAM_CLK,
        output wire [1:0] USB_STREAM_FIFOADDR,
        output wire USB_STREAM_PKTEND_N,
        input wire [2:0] USB_STREAM_FLAGS_N,
        output wire USB_STREAM_SLOE_n,
        output wire USB_STREAM_SLRD_n,
        output reg USB_STREAM_SLWR_n,
        inout wire [15:0] USB_STREAM_DATA,
        input wire USB_STREAM_FX2Rdy,

		//IO
        output wire [7:0] LED,
	    inout wire SCL_OUT, SDA_OUT, SCL_IN, SDA_IN
);

wire BUS_CLK;	
/*
wire CLK0_FB, CLK0;
DCM #(
		.CLKDV_DIVIDE(4), // Divide by: 1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0,6.5
		// 7.0,7.5,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0 or 16.0
		.CLKFX_DIVIDE(5), // Can be any Integer from 1 to 32
		.CLKFX_MULTIPLY(5), // Can be any Integer from 2 to 32
		.CLKIN_DIVIDE_BY_2("FALSE"), // TRUE/FALSE to enable CLKIN divide by two feature
		.CLKIN_PERIOD(20.833), // Specify period of input clock
		.CLKOUT_PHASE_SHIFT("NONE"), // Specify phase shift of NONE, FIXED or VARIABLE
		.CLK_FEEDBACK("1X"), // Specify clock feedback of NONE, 1X or 2X
		.DESKEW_ADJUST("SYSTEM_SYNCHRONOUS"), // SOURCE_SYNCHRONOUS, SYSTEM_SYNCHRONOUS or
		// an Integer from 0 to 15
		.DFS_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for frequency synthesis
		.DLL_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for DLL
		.DUTY_CYCLE_CORRECTION("TRUE"), // Duty cycle correction, TRUE or FALSE
		.FACTORY_JF(16'hC080), // FACTORY JF values
		.PHASE_SHIFT(0), // Amount of fixed phase shift from -255 to 255
		.STARTUP_WAIT("TRUE") // Delay configuration DONE until DCM_SP LOCK, TRUE/FALSE
		) DCM_BUS (
		.CLKFB(CLK0_FB), 
		.CLKIN(BUS_CLK_IN), 
		.DSSEN(1'b0), 
		.PSCLK(1'b0), 
		.PSEN(1'b0), 
		.PSINCDEC(1'b0), 
		.RST(1'b0),
		.CLKDV(),
		.CLKFX(), 
		.CLKFX180(), 
		.CLK0(CLK0), 
		.CLK2X(), 
		.CLK2X180(), 
		.CLK90(), 
		.CLK180(), 
		.CLK270(), 
		.LOCKED(), 
		.PSDONE(), 
		.STATUS());
		
assign CLK0_FB = BUS_CLK;
BUFG CLK_REG_BUFG_INST (.I(CLK0), .O(BUS_CLK));
*/
BUFG CLK_REG_BUFG_INST (.I(BUS_CLK_IN), .O(BUS_CLK));

wire BUS_RST;
reset_gen ireset_gen(.CLK(BUS_CLK), .RST(BUS_RST));

// -------  BUS SYGNALING  ------- //
wire BUS_RD, BUS_WR;
wire [15:0] BUS_ADD;
assign BUS_RD = !BUS_RD_N && !BUS_CS_N && !BUS_OE_N;
assign BUS_WR = !BUS_WR_N && !BUS_CS_N; 
assign BUS_ADD = USB_BUS_ADD - 16'h2000;

// -------  MODULE ADREESSES ------- //
localparam VERSION = 8'h04;

localparam GPIO_BASEADDR = 16'h3000;
localparam GPIO_HIGHADDR = 16'h4000-1;

localparam I2C_BASEADDR = 32'h4000;
localparam I2C_HIGHADDR = 32'h5000-1;
// ------- MODULES  ------- //

reg RD_VERSION;
always@(posedge BUS_CLK)
	if(BUS_ADD == 16'h2000 && BUS_RD)
		RD_VERSION <= 1;
	else
		RD_VERSION <= 0;

assign BUS_DATA = (RD_VERSION) ? VERSION : 8'bz;

gpio 
#( 
    .BASEADDR(GPIO_BASEADDR), 
    .HIGHADDR(GPIO_HIGHADDR),
    .IO_WIDTH(8),
    .IO_DIRECTION(8'hff)
) i_gpio
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .IO(LED[7:0])
);


wire I2C_CLK_PRE, I2C_CLK;
clock_divider  #( .DIVISOR(480) ) i2c_clkdev ( .CLK(BUS_CLK), .RESET(BUS_RST), .CE(), .CLOCK(I2C_CLK_PRE) );
BUFG BUFG_I2C (  .O(I2C_CLK),  .I(I2C_CLK_PRE) );
	 
i2c 
#( 
  .BASEADDR(I2C_BASEADDR), 
  .HIGHADDR(I2C_HIGHADDR),
  .MEM_BYTES(8) 
)  i_i2c_out
(
  .BUS_CLK(BUS_CLK),
  .BUS_RST(BUS_RST),
  .BUS_ADD(BUS_ADD),
  .BUS_DATA(BUS_DATA),
  .BUS_RD(BUS_RD),
  .BUS_WR(BUS_WR),

  .I2C_CLK(I2C_CLK),
  .I2C_SDA(SDA_OUT),
  .I2C_SCL(SCL_OUT)
);

assign SDA_OUT = SDA_IN ? 1'bz : 1'b0;
assign SCL_OUT = SCL_IN ? 1'bz : 1'b0;

`ifndef COCOTB_SIM //for simulation
    PULLUP isda (.O(SDA_OUT)); 
    PULLUP iscl (.O(SCL_OUT)); 
    //pullup  isda (SDA_OUT); 
    //pullup  iscl (SCL_OUT); 
`endif
    

wire STREAM_CLK;
BUFG CLK_STREAM_BUFG_INST (.I(USB_STREAM_CLK), .O(STREAM_CLK));

wire STREAM_RST;
reset_gen reset_gen_stream(.CLK(STREAM_CLK), .RST(STREAM_RST));

/////
/////
/////

parameter stream_in_idle   = 1'b0;
parameter stream_in_write  = 1'b1;

reg current_stream_in_state;
reg next_stream_in_state;
reg [15:0] data_cnt;
reg [4:0] cnt;

assign USB_STREAM_PKTEND_N = ~(cnt == 5'hff);// 1'b1;
assign USB_STREAM_DATA[15:0] = data_cnt[15:0];
assign USB_STREAM_FIFOADDR = 2'b10;
assign USB_STREAM_SLRD_n = 1'b1;
assign USB_STREAM_SLOE_n = 1'b1;

//write control signal generation
always@(*)begin
	if((current_stream_in_state == stream_in_write) & (USB_STREAM_FLAGS_N[1] == 1'b1))
		USB_STREAM_SLWR_n <= 1'b0;
	else
		USB_STREAM_SLWR_n <= 1'b1;
end

//loopback mode state machine 
always@(posedge STREAM_CLK) begin
	if(STREAM_RST)
  		current_stream_in_state <= stream_in_idle;
    else
        current_stream_in_state <= next_stream_in_state;
end

//LoopBack mode state machine combo
always@(*) begin
	next_stream_in_state = current_stream_in_state;
	case(current_stream_in_state)
		stream_in_idle:begin
			if((USB_STREAM_FLAGS_N[1] == 1'b1) & (USB_STREAM_FX2Rdy == 1'b1))
				next_stream_in_state = stream_in_write;
			else
				next_stream_in_state = stream_in_idle;
		end
		stream_in_write:begin
			if(USB_STREAM_FLAGS_N[1] == 1'b0)
				next_stream_in_state = stream_in_idle;
			else
				next_stream_in_state = stream_in_write;
		end
		default: 
			next_stream_in_state = stream_in_idle;
	endcase
end


//data generator counter
always@(posedge STREAM_CLK) begin
	if(STREAM_RST)
		data_cnt <= 16'd0;
	else if(USB_STREAM_SLWR_n == 1'b0)
		data_cnt <= data_cnt + 16'd1;
end		

always@(posedge STREAM_CLK) begin
	if(STREAM_RST)
		cnt <= 0;
	else if(USB_STREAM_SLWR_n == 1'b0)
		cnt <= cnt + 1;
end		

 
endmodule
