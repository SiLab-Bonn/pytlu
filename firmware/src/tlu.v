/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University 
 * ------------------------------------------------------------
 */

`include "utils/reset_gen.v"
`include "utils/bus_to_ip.v"
`include "utils/clock_divider.v"
`include "utils/cdc_reset_sync.v"
`include "utils/ddr_des.v"

`include "gpio/gpio.v"

`include "i2c/i2c.v"
`include "i2c/i2c_core.v"
`include "utils/cdc_pulse_sync.v"

`include "tlu_clk_gen.v"

`include "tlu_master/tlu_master.v"
`include "tlu_master/tlu_master_core.v"
`include "tlu_master/tlu_ch_rx.v"
`include "tlu_master/tlu_tx.v"

`include "pulse_gen/pulse_gen.v"
`include "pulse_gen/pulse_gen_core.v"

`ifdef COCOTB_SIM //for simulation
    `include "utils/BUFG_sim.v" 
    `include "utils/IDDR_sim.v"
    `include "utils/DCM_sim.v"
    `include "utils/ODDR_sim.v"
`else
    `include "utils/IDDR_s3.v"
    `include "utils/ODDR_s3.v"
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
        input wire USB_STREAM_FX2RDY,

        //IO
        inout wire I2C_SCL_OUT, I2C_SDA_OUT,
        input wire I2C_SCL_IN, I2C_SDA_IN, 
        output wire [1:0] I2C_SEL,
        
        output wire [5:0] DUT_TRIGGER, DUT_RESET, 
        input  wire [5:0] DUT_BUSY, DUT_CLOCK,
        input  wire [3:0] BEAM_TRIGGER
        
);

//assign DUT_TRIGGER = {BEAM_TRIGGER, BEAM_TRIGGER[1:0]};
//assign DUT_RESET = DUT_BUSY;

(* KEEP = "{TRUE}" *) 
wire CLK320;  
(* KEEP = "{TRUE}" *) 
wire CLK160;
(* KEEP = "{TRUE}" *) 
wire CLK40;
(* KEEP = "{TRUE}" *) 
wire CLK16;
(* KEEP = "{TRUE}" *) 
wire BUS_CLK;
(* KEEP = "{TRUE}" *) 
wire CLK8;
(* KEEP = "{TRUE}" *) 
wire I2C_CLK;

wire CLK_LOCKED;

 tlu_clk_gen tlu_clk_gen(
    .CLKIN(BUS_CLK_IN),
    .BUS_CLK(BUS_CLK),
    .U1_CLK8(CLK8),
    .U2_CLK16(CLK16),
    .U2_CLK40(CLK40),
    .U2_CLK160(CLK160),
    .U2_CLK320(CLK320),
    .U2_LOCKED(CLK_LOCKED)
);

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

localparam I2C_BASEADDR = 16'h4000;
localparam I2C_HIGHADDR = 16'h5000-1;

localparam TLU_MASTER_BASEADDR = 16'h5000;
localparam TLU_MASTER_HIGHADDR = 16'h6000 - 1;
    
localparam PULSE_TEST_BASEADDR = 16'h6000;
localparam PULSE_TEST_HIGHADDR = 16'h7000 - 1;
    

// ------- MODULES  ------- //

reg RD_VERSION;
always@(posedge BUS_CLK)
    if(BUS_ADD == 16'h2000 && BUS_RD)
        RD_VERSION <= 1;
    else
        RD_VERSION <= 0;

assign BUS_DATA = (RD_VERSION) ? VERSION : 8'bz;

wire [7:0] GPIO;
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
    .IO(GPIO[7:0])
);


    
assign I2C_SEL = GPIO[1:0];

wire I2C_CLK_PRE;
clock_divider  #( .DIVISOR(480) ) i2c_clkdev ( .CLK(BUS_CLK), .RESET(BUS_RST), .CE(), .CLOCK(I2C_CLK_PRE) );
`ifdef COCOTB_SIM //for simulation
    BUFG BUFG_I2C (  .O(I2C_CLK),  .I(BUS_CLK) );
`else
    BUFG BUFG_I2C (  .O(I2C_CLK),  .I(I2C_CLK_PRE) );
`endif

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
  .I2C_SDA(I2C_SDA_OUT),
  .I2C_SCL(I2C_SCL_OUT)
);

//THIS CANOT BE DONE BCAUSE THE PCB DESIGN IS WRONG!!!
//assign I2C_SDA_OUT = I2C_SDA_IN ? 1'bz : 1'b0;
//assign I2C_SCL_OUT = I2C_SCL_IN ? 1'bz : 1'b0;

`ifndef COCOTB_SIM //for simulation
    PULLUP isda (.O(I2C_SDA_OUT)); 
    PULLUP iscl (.O(I2C_SCL_OUT)); 
`else
    pullup  isda (I2C_SDA_OUT); 
    pullup  iscl (I2C_SCL_OUT); 
`endif

wire TEST_PULSE;
pulse_gen
#( 
    .BASEADDR(PULSE_TEST_BASEADDR), 
    .HIGHADDR(PULSE_TEST_HIGHADDR)
) i_pulse_gen
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(CLK40),
    .EXT_START(1'b0),
    .PULSE(TEST_PULSE)
    );
    
wire TDC_MASTER_FIFO_READ, TDC_MASTER_FIFO_EMPTY;
wire [31:0] TDC_MASTER_FIFO_DATA;

tlu_master #(
    .BASEADDR(TLU_MASTER_BASEADDR),
    .HIGHADDR(TLU_MASTER_HIGHADDR)
) tlu_master (
    .CLK320(CLK320),
    .CLK160(CLK160),
    .CLK40(CLK40),
    
    .TEST_PULSE(TEST_PULSE),
    .DUT_TRIGGER(DUT_TRIGGER), .DUT_RESET(DUT_RESET), 
    .DUT_BUSY(DUT_BUSY), .DUT_CLOCK(DUT_CLOCK),
    .BEAM_TRIGGER(BEAM_TRIGGER),

    .FIFO_READ(TDC_MASTER_FIFO_READ),
    .FIFO_EMPTY(TDC_MASTER_FIFO_EMPTY),
    .FIFO_DATA(TDC_MASTER_FIFO_DATA),

    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR)
);



///
///
///

wire STREAM_CLK;
BUFG CLK_STREAM_BUFG_INST (.I(USB_STREAM_CLK), .O(STREAM_CLK));

wire STREAM_RST;
reset_gen reset_gen_stream(.CLK(STREAM_CLK), .RST(STREAM_RST));

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
            if((USB_STREAM_FLAGS_N[1] == 1'b1) & (USB_STREAM_FX2RDY == 1'b1))
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

 
wire CLK_1HZ;
clock_divider #(
  .DIVISOR(40000000)
) i_clock_divisor_40MHz_to_1Hz (
	  .CLK(CLK40),
	  .RESET(1'b0),
	  .CE(),
	  .CLOCK(CLK_1HZ)
);

//assign DUT_TRIGGER = {6{CLK_1HZ}};
//assign DUT_RESET = DUT_BUSY;

endmodule
