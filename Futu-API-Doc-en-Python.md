# OpenAPI Introduction

# Overview

OpenAPI provides wide varieties of market data and trading services for your programmed trading to meet the needs of every developer's programmed trading and help your Quant dreams. 

Futubull users can click here to learn more. 

OpenAPI consists of OpenD and Futu API: 

OpenD is the gateway program of Futu API, running on your local computer or cloud server. It is responsible for transferring the protocol requests to Futu servers, and returning the processed data. 

Futu API is an API SDK encapsulated by Futu, including mainstream programming languages (Python, Java, C#, ${ \mathsf { C } } + + ,$ JavaScript), to reduce the difficulty of your trading strategy development. If the language you want to use is not listed above, you can still interface with the protocol yourself to complete the trading strategy development. 

Diagrams below illustrate the architecture of OpenAPI. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/29bac0f7c0edee6c073d6055a7a4c1cdc0a85d7ded788ad676acb56198d583a9.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/1187074720232703acc10f8799404ebb86d2739f6f8a1ae604e8493ce493df6a.jpg)


The first time using OpenAPI, you need to finish the following two steps: 

The first step is to install and start a gateway program OpenD locally or in the cloud. 

OpenD exposes the interfaces in the way of TCP, which is responsible for transferring the protocol requests to Futu Server and returning the processed data. The protocol interface has nothing to do with the type of programming language. 

The second step is to download Futu API and complete Environment Setup. 

For your convenience, Futu encapsulates API SDK for mainstream programming languages (hereinafter referred to as Futu API). 

# Account

OpenAPI involves two types of accounts, Futu ID and universal account. 

# Futu ID

Futu ID is your user account (Futubull ID ), which can be used in Futubull APP and OpenAPI. You can use your Futu ID and login password to log in to OpenD and obtain market data. 

# Universal Account

Universal account allows trading across multiple markets (including Hong Kong stocks, US stocks, A-shares, and funds) in various currencies. There's no need for multiple accounts. Universal Accounts come in two forms: 

Securities Universal Account: Trade stocks, ETFs, options, and other securities across different markets. 

Futures Universal Account: Trade futures, including Hong Kong, US CME Group, Singapore, and Japanese futures. 

# Functionality

There are 2 functions of OpenAPI: quotation and trading. 

# Quotation Functions

# Quotation Data Categories

Including stocks, indices, options and futures from HK, US and A-share market. Find the specific types of support in the table below. You need authorities for each kinds of market data. For more details on how to obtain authorities, please click here. 

<table><tr><td>Market</td><td>Contract</td><td>Futu Users</td></tr><tr><td rowspan="5">HK Market</td><td>Stocks, ETFs, Warrants, CBBCs, Inline Warrants</td><td>✓</td></tr><tr><td>Options</td><td>✓</td></tr><tr><td>Futures</td><td>✓</td></tr><tr><td>Indices</td><td>✓</td></tr><tr><td>Plates</td><td>✓</td></tr><tr><td rowspan="6">US Market</td><td>Stocks, ETFs</td><td>✓</td></tr><tr><td>OTC Securities</td><td>X</td></tr><tr><td>Options</td><td>✓</td></tr><tr><td>Futures</td><td>✓</td></tr><tr><td>Indices</td><td>X</td></tr><tr><td>Plates</td><td>✓</td></tr><tr><td rowspan="3">A-share Market</td><td>Stocks, ETFs</td><td>✓</td></tr><tr><td>Indices</td><td>✓</td></tr><tr><td>Plates</td><td>✓</td></tr><tr><td rowspan="2">Singapore Market</td><td>Stocks, ETFs, Warrants, REITs, DLCs</td><td>X</td></tr><tr><td>Futures</td><td>X</td></tr><tr><td rowspan="2">Japanese Market</td><td>Stocks, ETFs, REITs</td><td>X</td></tr><tr><td>Futures</td><td>X</td></tr><tr><td>Australian Market</td><td>Stocks, ETFs</td><td>X</td></tr><tr><td>Global Markets</td><td>Forex</td><td>X</td></tr></table>

# Method to Obtain Market Data

Subscribe and receive pushed real-time quote, candlestick, tick-by-tick and order book. 

Request for the latest market snapshot, historical candlesticks etc. 

# Trading Functions

# Trading Capacity

Including stocks, options and futures from HK, US, A-share, Singapore and Japanese markets. Find the specific types of support in the table below: 

<table><tr><td rowspan="2">Market</td><td rowspan="2">Contracts</td><td rowspan="2">Paper Trading</td><td colspan="7">Live Trading</td></tr><tr><td>FUTU HK</td><td>Moomoo US</td><td>Moomoo SG</td><td>Moomoo AU</td><td>Moomoo MY</td><td>Moomoo CA</td><td>Moomoo JP</td></tr><tr><td rowspan="3">HK Market</td><td>Stocks,ETFs,Warrants,CBBCs,InlineWarrants</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>X</td><td>X</td></tr><tr><td>Options</td><td>✓</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Futures</td><td>✓</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td rowspan="3">US Market</td><td>Stocks,ETFs</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Options</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Futures</td><td>✓</td><td>✓</td><td>X</td><td>✓</td><td>X</td><td>✓</td><td>X</td><td>X</td></tr><tr><td rowspan="2">A-share Market</td><td>ChinaConnectSecuritiesstocks</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>X</td><td>✓</td><td>X</td><td>X</td></tr><tr><td>Non-ChinaConnectSecuritiesstocks</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td rowspan="2">Singapore Market</td><td>Stocks,ETFs,Warrants,REITs,DLCs</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Futures</td><td>✓</td><td>✓</td><td>X</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td rowspan="2">Japanese Market</td><td>Stocks,ETFs,REITs</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Futures</td><td>✓</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Australian Market</td><td>Stocks,ETFs</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Canadian Market</td><td>Stocks,ETFs</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr></table>

# Method of Trading

The trading interfaces are used for both live trading and paper trading. 

# Features

1. Full platform and multi-language 

OpenD supports Windows, MacOS, CentOS, Ubuntu 

Futu API supports Python, Java, C#, ${ \mathsf { C } } + + ,$ , JavaScript, etc. 

2. Stable speed and free 

Stable technical architecture, directly connected to the exchanges 

The fastest order is 0.0014s 

There is no additional charge for trading via OpenAPI 

3. Abundant investment varieties 

Supporting real-time market data, live trading, and simulated trading in multiple markets including United States, Hong Kong, etc. 

4. Professional institutional services 

Customized market data and trading solutions 

# Authorities and Limitations

# Login Limitations

# Opening Accounts

You need to finish opening your trading accounts on Futubull APP, before logging in to OpenAPI. 

# Compliance Confirmation

After the first login, you need to complete API Questionnaire and Agreements before you can continue to use OpenAPI. Click here for Futubull users. 

# Quotation Data

There are several limitations for market quotation data as follow: 

Quote Right -- The authority to obtain the relevant market data. 

Interface Frequency Limitations -- Frequency limits of calling interfaces. 

Subscription Quota -- Number of real-time quotes subscribed at the same time. 

Historical Candlestick Quota -- The total number of subjects pulling the historical candlestick per 30 days. 

# Quote Right

You need the corresponding permission to obtain data of each market through OpenAPI. The permission of OpenAPI is not exactly the same as that of APP. Different levels correspond to different time delay, order book levels, and the permission to use the interface. 

You need to buy a quotation card before you can obtain the quotation of some varieties, the specific way to obtain is shown in the table below. 

Market 

Security Type 

Quote Right Acquisition Method 

<table><tr><td rowspan="5">HK Market</td><td>Securities (including stocks, ETFs, warrants, CBBCs, Inline Warrants)</td><td rowspan="3">* Chinese mainland customers: LV2 market quotes for free. Purchase HK Stocks Advanced Full Market Quotes for SF market quotes
* Non-Chinese mainland customers: LV1 market quotes for free. Purchase HK stocks LV2 advanced market for LV2 market quotes.
Purchase HK Stocks Advanced Full Market Quotes for SF market quotes</td></tr><tr><td>Indices</td></tr><tr><td>Plates</td></tr><tr><td>Options</td><td rowspan="2">* Chinese mainland customers: LV2 market quotes for free during promotion period.
* Non-Chinese mainland customers: LV1 market quotes for free. Purchase HK stock options futures LV2 advanced market for LV2 market data</td></tr><tr><td>Futures</td></tr><tr><td rowspan="5">US Market</td><td>Securities (Covers NYSE, NYSE-American and Nasdaq listed equities, ETFs)</td><td rowspan="2">* Not shared with App market data permissions. Purchase Nasdaq Basic for LV1 market quotes (basic quotes, 24H).
* Not shared with App market data permissions. Purchase Nasdaq Basic+TotalView for LV2 market quotes (Full Order Book for 24H trading).</td></tr><tr><td>Plates</td></tr><tr><td>OTC Securities</td><td>Unsupported.</td></tr><tr><td>Options (Covers US stock options, US index options)</td><td>* Customers who meet the threshold : get LV1 market data for free
* Customers who do not meet the threshold : Purchase OPRA Options Real-time Quote for LV1 market data</td></tr><tr><td>Futures</td><td>* For clients who have a futures account.
For CME Group quotes please access the CME Group Futures LV2
For CME quotes, please access the CME Futures LV2
For CBOT quotes, please access the CBOT Futures LV2
For NYMEX quotes, please access the NYMEX Futures LV2
For NYMEX quotes, please access the COMEX Futures LV2
* For clients who do not have a futures account:Unsupported.</td></tr><tr><td></td><td>Indices</td><td>Unsupported.</td></tr><tr><td rowspan="3">A-share Market</td><td>Securities (including stocks, ETFs)</td><td rowspan="3">* Chinese mainland customers: LV1 market data for free.
* Non-Chinese mainland customers/institutional customers:Unsupported.</td></tr><tr><td>Indices</td></tr><tr><td>Plates</td></tr><tr><td>Singapore Market</td><td>Futures</td><td>Unsupported.</td></tr><tr><td>Japanese Market</td><td>Futures</td><td>Unsupported.</td></tr></table>

# Tips

In the above table, the Chinese mainland customers and the Non-Chinese mainland customers are distinguished by the login IP address of OpenD. 

# Interface Frequency Limitations

In order to protect the server from malicious attacks, there are frequency limitations for all interfaces that need to send requests to Futu servers. The frequency limitation rules for each API are different. For more information, please see Interface Limitations at the bottom of each API page. 

# Example:

The limitation rule of Get Market Snapshot is: A maximum of 60 requests every 30 seconds. You can request a uniform request every 0.5 seconds. You can also quickly request 60 times, rest for 30 seconds, and then request the next round. If the frequency limitation is exceeded, an error will be returned by the interface. 

# Subscription Quota & Historical Candlestick Quota

The limitation rules of subscription quota and historical candlestick quota as follows: 

<table><tr><td>User Type</td><td>Subscription Quota</td><td>Historical Candlestick Quota</td></tr><tr><td>Finished Opening trading accounts.</td><td>100</td><td>100</td></tr><tr><td>Total asset &gt; 10,000 HKD.</td><td>300</td><td>300</td></tr><tr><td>Satisfy 1 of the items following: 
1. Total asset &gt; 500,000 HKD;
2. The number of monthly filled orders &gt; 200;
3. Monthly trading volume &gt; 2 million HKD.</td><td>1000</td><td>1000</td></tr><tr><td>Satisfy 1 of the items following: 
1. Total asset &gt; 5 million HKD;
2. The number of monthly filled orders &gt; 2000;
3. Monthly trading volume &gt; 20 million HKD.</td><td>2000</td><td>2000</td></tr></table>

# 1. Total asset

Total asset，refers to all your assets in Futu, including securities, futures, funds and bonds assets, converted into HKD according to the spot exchange rate. 

# 2. The monthly number of filled orders

It is calculated by taking the larger value of the number of filled orders the last natural month and that of the current natural month, that is: 

max (the number of filled orders of the last natural month, the number of filled orders of the current natural month) 

# 3. Monthly Trading volume

It is calculated by taking the larger value of the total trading volume of your last natural month and that of the current natural month, which is converted into HKD according to the spot exchange rate, that is: 

max (the total trading volume of the last natural month, the total trading volume of the current natural month) 

The calculation of futures trading value needs to be multiplied by the adjustment factor (0.1 by default). The formula for calculating futures trading volume is as follows: 

Futures trading value $= \Sigma$ (volume of a single transaction * trading price * contract multiplier * exchange rate * adjustment factor) 

# 4. Subscription Quota

It is applicable to the real-time data interface that can only be obtained after a subscription. 

One type of subscription for each stock takes up 1 subscription quota, and canceling the 

subscription will release the occupied quota. 

# Example:

Suppose your Subscription Quota is 100. When you subscribe to real-time order book for HK.00700, real-time ticker for US.AAPL, and real-time quotation for SH.600519 at the same time, the Subscription Quota will occupy 3, and the remaining Subscription Quota will be 97. At this time, if you cancel the real-time order book subscription of HK.00700, your Subscription Quota will become 2, and the remaining Subscription Quota will become 98. 

# 5. Historical Candlestick Quota

Suitable for Get Historical Candlesticks interface. In the last 30 days, requests for historical candlesticks of each stock will occupy one Historical Candlestick Quota. Repeated requests for historical candlestick of the same stock within the last 30 days will not be counted repeatedly. Example: 

Suppose your Historical Candlestick Quota is 100, and today is July 5, 2020. You have requested historical candlesticks for a total of 60 stocks between June 5, 2020 and July 5, 2020. The remaining Historical Candlestick Quota is 40. 

# Tips

Subscription Quota and Historical Candlestick Quota are automatically assigned and do not need to be applied manually. 

For newly deposited accounts, the quota will automatically take effect within 2 hours. 

Asset in Transit will not be calculated in quota assign. 

# Trading Functions

When you trade in a specific market, you need to first confirm whether a trading account has been opened in that market. 

For example: you can only trade US stocks under the US trading account, but not under the HK trading account. 

# Fee

# Quote

LV2 HK market quotes and A-share LV1 market quotes are free for Chinese mainland customers. 

For some variaties, you need to buy quotation cards before obtaining market data. For more details of quotation cards prices, please click Quote Right and go to data store. 

# Trade

There is no extra fee for tradings through OpenAPI. The transaction fee is the same as that of APP. You can check the specific charging plans from the following table: 

<table><tr><td>Securities Firm</td><td>Charging Options</td></tr><tr><td>FUTU HK</td><td>Charging Options ☑</td></tr><tr><td>Moomoo US</td><td>Charging Options ☐</td></tr><tr><td>Moomoo SG</td><td>Charging Options ☐</td></tr><tr><td>Moomoo AU</td><td>Charging Options ☑</td></tr><tr><td>Moomoo MY</td><td>Charging Options ☑</td></tr><tr><td>Moomoo CA</td><td>Charging Options ☐</td></tr><tr><td>Moomoo JP</td><td>Charging Options ☐</td></tr></table>

# Visualization OpenD

OpenD provides two operation modes: visualization and command line. Here is a description of Visualization OpenD which is relatively simple to operate. 

Please refer to Command Line FutuOpenD for more informations for your interest. 

# Visualization OpenD

# Step 1: Download

Visualization OpenD can be runned under 4 operating systems: Windows、MacOS、CentOS、 Ubuntu (Click to download). 

. OpenD - Windows 、MacOS 、CenOS 、Ubuntu 

# Step 2: Installation

Extract the file and find the corresponding installation file to install OpenD. 

OpenD is installed in the % appdata% directory by default under Windows System. 

# Step 3: Configuration

The Visualization OpenD launch configuration is on the right side of the graphical interface, as shown in the following figure: 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/3f49787c666a7063d02bc71b6e75eae352027380213613ce0463b953c0b0ddf2.jpg)


# Futu OpenD Login

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/b460ff6c4797fe20a418029e7ddb2e4d63a746c37b69052486643306f7cc87ae.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/1c9da64bdec99c081373409209103e9f7ae6485341e55c09dada54578f11ac28.jpg)


# Basic

# Advanced

# Configuration item list：

<table><tr><td>Configuration Item</td><td>Description</td></tr><tr><td>IP</td><td>API listening IP address.</td></tr><tr><td>Port</td><td>API listening port.</td></tr><tr><td>Log Level</td><td>Log level of OpenD.</td></tr><tr><td>Language</td><td>Language.</td></tr><tr><td>Time Zone of Future Trade API</td><td>Specify the futures trading API time zone.</td></tr><tr><td>Data Push Frequency</td><td>API subscription data push frequency control.</td></tr><tr><td>Telnet IP</td><td>Listening address of remote operation command.</td></tr><tr><td>Telnet Port</td><td>Listening port of remote operation command.</td></tr><tr><td>Encrypted Private Key</td><td>Absolute path of RSA Encrypted Private Key.</td></tr><tr><td>WebSocket IP</td><td>WebSocket listening address.</td></tr><tr><td>WebSocket Port</td><td>WebSocket listening port.</td></tr><tr><td>WebSocket Certificate</td><td>WebSocket certificate file path.</td></tr><tr><td>WebSocket Private Key</td><td>WebSocket certificate private key file path.</td></tr><tr><td>WebSocket Authentication Key</td><td>Cipher text of key (32-bit MD5 encrypted hexadecimal).</td></tr></table>

# Tips

Visual OpenD provides services by launching command line OpenD, interacted through WebSocket, so the WebSocket function must be started. 

To ensure safety of your trading accounts, if the listening address is not local, you must configure a private key to use the trading interface. The quote interface is not subject to this restriction. 

When the WebSocket listening address is not local, you need to configure SSL to start it, and a password should not be set during the certificate private key generation. 

Ciphertext is represented in hexadecimal after plaintext is encrypted by 32-bit MD5, which can be calculated by searching online MD5 encryption (note that there may be a risk of records colliding with libraries calculated through third-party websites) or by downloading MD5 computing tools. The 32-bit MD5 ciphertext is shown in the red box area (e10adc3949ba59abbe56e057f20f883e): 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/c02d191ef336ec19aa72a4849345c6dc46f1c364c4c0d53c04f493a8435c4330.jpg)


Result: 

md5(123456,32) $=$ e10adc3949ba59abbe56e057f20f883e 

md5(123456,16) $\overline { { \mathbf { \Omega } } } = \mathbf { \Omega }$ 49ba59abbe56e057 

OpenD reads OpenD.xml in the same directory by default. On MacOS, due to the system protection mechanism, FutuOpenD.app will be assigned a random path at 

run time, so that the original path can not be found. At this point, there are the following methods: 

Execute fixrun.sh under tar package 

Specify the configuration file path with the command line parameter cfg_file , as described below 

The log level defaults to the info level. During the system development phase, it is not recommended to close the log or modify the log to the warning, error, fatal level to prevent failure to locate problems. 

# Step 4: Login

. Enter your account number and password to login. 

You need to complete the questionnaire evaluation and agreement confirmation when you log in for the first time. 

You can see your account information and quote right, After logging in successfully. 

# Environment Setup

Notice 

Ways of building programming environment are different for different programming languages. 

# Python Environment

# Environment Requirement

. Operating system requirements: 

32-bit or 64-bit operating system of Windows 7/10 

64-bit operating system of Mac 10.11 and above 

64-bit operating system of CentOS 7 and above 

64-bit operating system of Ubuntu 16.04 and above 

Python version requirements: 

Python 3.6 or above 

# Environment Building

# 1. Install Python

To avoid running failures due to environmental problems, we recommend Python version 3.8. 

Download page: Download Python 

Tips 

After the installation, execute the following command to see if the installation is successful: 

python -V (Windows) or python3 -V (Linux/Mac) 

# 2. Install PyCharm (Optional)

We recommend that using PyCharm as your Python IDE. 

# 3. Install TA-Lib (Optional)

TA-Lib is a functional library widely used in program trading for technical analysis of market data. It provides a variety of technical analysis functions to facilitate our quantitative investment. 

Installation method: directly use pip installation in cmd 

$\because$ pip install TA-Lib 

# 提⽰

Installation of TA-Lib is not necessary, you can skip this step 

# Program Samples

# Python Example

# Step 1: Download and install OpenD

Please refer to here to finish downloading, installing and logging in OpenD. 

# Step 2: Download Python API

. Method 1: Use pip install in cmd. 

Initial installation: Windows: $\because$ pip install futu-api , Linux/Mac $ pip3 install futu-api . 

Secondary upgrade: Windows: $^ { - 1 }$ pip install futu-api --upgrade ，Linux/Mac $ pip3 install futu-api --upgrade 

. Method 2: Click to download latest version of Python API . 

# Step 3: Create New Project

Open PyCharm and click 'New Project' from 'Welcome to PyCharm' window. If you have already created a project, you can open the project directly. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/d5aa4b8c3f9eb553b9f212efd53d28a085621f0321bd14520e7d0d23c03dbdb4.jpg)


# Step 4: Create new file

Create new Python file under the project, and copy the sample code below to that file. The sample code includes viewing the market snapshot and placing an order through paper trading account. 

```python
1 from futu import *
2 quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111) # Create quote object
3 quoteCtx.get_market_snapshot('HK.00700')) # Get market snapshot for HK.00
4 quoteCtx.close() # Close object to prevent the number of connections from running
5 quoteCtx.close()
6 trdCtx = OpenSecTradeContext(host='127.0.0.1', port=11111) # Create trade object
7 print(trdCtx.place_order(price=500.0, qty=100, code="HK.00700", trdSide=TrdSide)
8 trdCtx.close()
9 quoteCtx.close()
10 
```

# Step 5: Running file

Run the project, and you can see the returned message of a successful run as follows: 

```csv
2020-11-05 17:09:29,705 [open_context_base.py] _socket_reconnect_and_wait_ready:2  
2020-11-05 17:09:29,705 [open_context_base.py] on-connected:344: Connected : conn  
2020-11-05 17:09:29,706 [open_context_base.py] _handle_init_connect:445: InitConn  
(0, code update_time last_price open_price high_price ... a  
0 HK.00700 2020-11-05 16:08:06 625.0 610.0 625.0 ...  
[1 rows x 132 columns])  
2020-11-05 17:09:29,739 [open_context_base.py] _socket_reconnect_and_wait_ready:2  
2020-11-05 17:09:29,739 [networkmanager.py] work:366: Close: conn_id=1  
2020-11-05 17:09:29,739 [open_context_base.py] on connected:344: Connected : conn  
2020-11-05 17:09:29,740 [open_context_base.py] _handle_init_connect:445: InitConn  
(0, code stock_name trd_side order_type order_status ... dealt_avg_price  
0 HK.00700 腾讯控股 BUY NORMAL SUBMITTING ... 0.0  
[1 rows x 16 columns])  
2020-11-05 17:09:32,843 [networkmanager.py] work:366: Close: conn_id=2  
(0, code stock_name trd_side order_type order_status ... dealt_avg_p  
0 HK.00700 腾讯控股 BUY ABSOLUTE_LIMIT SUBMITTED ...  
[1 rows x 16 columns])
```

# Strategy Setup

# Tips

The content of this trading strategy is not an investment advice. It is for learning purposes only. 

# Strategy Introduction

Contruct a Double Moving Averaging Strategy. 

That is, using the 1 minute candlestick of an underlying stock, to calculate two moving averages of different periods, MA1 and MA3. The values of MA1 and MA3 are tracked to determine the timing of buying and selling. 

When MA1 >= MA3, the underlying stock is judged to be strong and the market is considered to be a bull market, which shows a long signal. 

When MA1 < MA3, the underlying stock is judged to be weak and the market is considered to be a bear market, which shows a short signal. 

# Flow Chart

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/2933b392e33542562fab00cd228013c014d26882f4b05a578d922395e33ccbb1.jpg)


# Code Sample

Example 

from futu import * 

############################ Global Variables ############################ 

FUTU_OPEND_ADDRESS = '127.0.0.1' # OpenD listening address 

FUTU_OPEND_PORT = 11111 # OpenD listening port 

TRADING_ENVIRONMENT = TrdEnv.SIMULATE # Trading environment: REAL / SIMULATE 

TRADING_MARKET = TrdMarket.HK # Transaction market authority, used to filter acc 

TRADING_PWD = '123456' # Trading password, used to unlock trading for real trad 

TRADING_PERIOD = KLType.K_1M # Underlying trading time period 

TRADING_SECURITY = 'HK.00700' # Underlying trading security code 

FAST_MOVING_AVERAGE = 1 # Parameter for fast moving average 

SLOW_MOVING_AVERAGE = 3 # Parameter for slow moving average 

quote_context = OpenQuoteContext(host=FUTU_OPEND_ADDRESS, port=FUTU_OPEND_PORT) 

trade_context = OpenSecTradeContext(filter_trdmarket=TRADING_MARKET, host=FUTU_OP 

# Unlock trade 

def unlock_trade(): 

if TRADING_ENVIRONMENT == TrdEnv.REAL: 

ret, data = trade_context.unlock_trade(TRADING_PWD) 

if ret != RET_OK: 

print('Unlock trade failed: ', data) 

return False 

print('Unlock Trade success!') 

return True 

# Check if it is regular trading time for underlying security 

def is_normal_trading_time(code): 

ret, data = quote_context.get_market_state([code]) 

if ret != RET_OK: 

print('Get market state failed: ', data) 

return False 

market_state = data['market_state'][0] 

MarketState.MORNING 

HK and A-share morning 

MarketState.AFTERNOON 

HK and A-share afternoon, US opening hours 

MarketState.FUTURE_DAY_OPEN 

HK, SG, JP futures day market open 

MarketState.FUTURE_OPEN 

US futures open 

MarketState.FUTURE_BREAK_OVER 

Trading hours of U.S. futures after break 

MarketState.NIGHT_OPEN 

HK, SG, JP futures night market open 

```python
if market_state == MarketState.MORNING or \
    market_state == MarketState.AFTERNOON or \
    market_state == MarketState.FUTURE_DAY_OPEN or \
    market_state == MarketState.FUTURE_OPEN or \
    market_state == MarketState.FUTURE_BREAK_OVER or \
    market_state == MarketState.NIGHT_OPEN:
        return True
print('It is not regular trading hours.')
return False
# Get positions
def get_holding_position(code):
    holding_position = 0
ret, data = trade_context.position_list_query(code=code, trd_env=TRADING_env)
if ret != RET_OK:
    print('Get holding position failed: ', data)
    return None
else:
    for qty in data['qty'].values.tolist():
        holding_position += qty
print(['Holding Position Status] The hedlng position quantity of {} is:
return holding_position
# Query for candlesticks, calculate moving average value and judge bull or bear
def calculate_bull_bear(code, fast-param, slow-param):
    if fast-param <= 0 or slow-param <= 0:
        return 0
    if fast-param > slow-param:
        return calculate_bull_bear(code, slow-param, fast-param)
ret, data = quote_context.get.cur_kline(code=code, num=slow-param + 1, ktype=0)
if ret != RET_OK:
    print('Get candlestick value failed: ', data)
return 0
candlestick_list = data['close'].values.tolist()[:-1]
fast_value = None
slow_value = None
if len(candlestick_list) > fast-param:
    fast_value = sum(candlestick_list[1: fast-param + 1]) / fast-param
if len(candlestick_list) > slow-param:
    slow_value = sum(candlestick_list[1: slow-param + 1]) / slow-param
if fast_value is None or slow_value is None:
    return 0 
```

```python
return 1 if fast_value >= slow_value else -1
# Get ask1 and bid1 from order book
def get Asking_and_bidcode:
    ret, data = quote_context.get_order_book(code, num=1)
    if ret != RET_OK:
        print('Get order book failed: ', data)
        return None, None
    return data['Ask'] [0][0], data['Bid'] [0][0]
# Open long positions
def open_position(code):
    # Get order book data
    ask, bid = get Asking_and_bid(code)
    # Get quantity
    openquantity = calculatequantity()
    # Check whether buying power is enough
    if is_validquantity(TRADING_SECURITY, openquantity, ask):
        # Place order
        ret, data = trade_context.place_order(price=ask, qty=openquantity, code=order_type=OrderType.NORMAL, trdRemark='moving_average_strategy')
    if ret != RET_OK:
        print('Open position failed: ', data)
    else:
        print('Maximum quantity that can be bought less than transaction quantity')
# Close position
def close_position(code, quantity):
    # Get order book data
    ask, bid = get Asking_and_bid(code)
    # Check quantity
    if quantity == 0:
        print('Invalid order quantity.')
    return False
# Close position
ret, data = trade_context.place_order(price=bid, qty=quantity, code=code, trdorder_type=OrderType.NORMAL, trd_env=TRADING_environment, rema 
```

if ret != RET_OK: print('Close position failed: ', data) return False return True   
# Calculate order quantity   
def calculatequantity(): pricequantity $= 0$ # Use minimum lot size ret, data $=$ quote_context.get_market_snapshot([TRADING_SECURITY]) if ret != RET_OK: print('Get market snapshot failed: ', data) return pricequantity pricequantity $=$ data['lot_size'] [0] return pricequantity   
# Check the buying power is enough for the quantity   
def is_valid�数量码，qunity，price): ret，data $=$ trade_context.acctradinginfo_query(order_type $\equiv$ OrderType.NORMAL, trd_env $\equiv$ TRADING_ENVIRONMENT) ifret $! =$ RET_OK: print('Get max long/short quantity failed: ',data) return False max_can_buy $=$ data['max_cash_buy'] [0] max_can_buy $=$ data['max_buy_short'] [0] ifquantity>0: return quantity $<$ max_can_buy elif quantity $<  0$ : return abs(qutiny) $<$ max_can_buy else: return False   
# Show order status   
def show_order_status(data): order_status $=$ data['order_status'] [0] order_info $=$ dict() order_info['Code'] $=$ data['code'] [0] order_info['Price'] $=$ data['price'] [0] order_info['TradeSide'] $=$ data['trd_side'] [0] order_info['Quantity'] $=$ data['qty'] [0] print(['OrderStatus'],order_status,order_info)

```python
# Strategy initialization. Run once when the strategy starts
def on_init():
    # unlock trade (no need to unlock for paper trading)
    if not unlock_trade():
        return False
        print('****** Strategy Starts ____________')
    return True
# Run once for each tick. You can write the main logic of the strategy here
def on Tick():
    pass
# Run once for each new candlestick. You can write the main logic of the strategy
def on_bar_open():
    # Print seperate line
    print('____________________________')
    # Only trade during regular trading hours
    if not is_normal_trading_time(TRADING_SECURITY):
        return
    # Query for candlesticks, and calculate moving average value
    bull_or_bear = calculate_bull_bear(TRADING_SECURITY, FAST_MOVING_AVERAGE, SLG)
    # Get positions
    holding_position = get_holding_position(TRADING_SECURITY)
    # Trading signals
    if holding_position == 0:
        if bull_or_bear == 1:
            print(['[Signal] Long signal. Open long positions.'] 
            open_position(TRADING_SECURITY)
            else:
                print(['[Signal] Short signal. Do not open short positions.'] 
elif holding_position > 0:
    if bull_or_bear == -1:
        print(['[Signal] Short signal. Close positions.'] 
close_position(TRADING_SECURITY, holding_position)
else:
    print(['[Signal] Long signal. Do not add positions.'] 
```

```python
# Run once when an order is filled
def on_fill(data):
    pass
# Run once when the status of an order changes
def on_order_status(data):
    if data['code'].[0] == TRADINGSECURITY:
        show_order_status(data)
#****************# Framework code, which can be ignored****************#
class OnTickClass(TickerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        on Tick()
class OnBarClass(CurKlineHandlerBase):
    last_time = None
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(OnBarClass, self).on_recv_rsp(rsp_pb)
        if ret_code == RET_OK:
            cur_time = data['time_key'].[0]
            if cur_time != self.last_time and data['k_type'].[0] == TRADINGPERIOD:
                if self.last_time is not None:
                    on_bar_open()
                    self.last_time = cur_time
class OnOrderClass(TradeHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret, data = super(OnOrderClass, self).on_recv_rsp(rsp_pb)
        if ret == RET_OK:
            on_order_status(data)
class OnFillClass(TradeDealHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret, data = super(OnFillClass, self).on_recv_rsp(rsp_pb)
        if ret == RET_OK:
            on_fill(data)
# Main function 
```

```python
270 if _name_ == '__main__':  
271 # Strategy initialization  
272 if not on_init():  
273 print('Strategy initialization failed, exit script!')  
274 quote_context.close()  
275 trade_context.close()  
276 else:  
277 # Set up callback functions  
278 quote_context.set handler(OnTickClass())  
279 quote_context.set handler(OnBarClass())  
280 trade_context.set handler(OnOrderClass())  
281 trade_context.set handler(OnFillClass())  
282  
283 # Subscribe tick-by-tick, candlestick and order book of the underlying to  
284 quote_context.subscribe(code_list=[TRADING_SECURITY], subtype_list=[SubTy]  
285 
```


Output


```txt
1 ******Strategy Starts ******  
2 ****** ****** ******  
3 [Position] The position of HK.00700 is 0  
4 [Signal] Long signal. Open long positions.  
5 [OrderStatus] SUBMITTING {'Code': 'HK.00700', 'Price': 597.5, 'TradeSide': 'BUY'  
6 [OrderStatus] SUBMITTED {'Code': 'HK.00700', 'Price': 597.5, 'TradeSide': 'BUY',  
7 [OrderStatus] FILLED_ALL {'Code': 'HK.00700', 'Price': 597.5, 'TradeSide': 'BUY'  
8 ****** ****** ******  
9 [Position] The position of HK.00700 is 100.0  
10 [Signal] Short signal. Close positions.  
11 [OrderStatus] SUBMITTING {'Code': 'HK.00700', 'Price': 596.5, 'TradeSide': 'SELL  
12 [OrderStatus] SUBMITTED {'Code': 'HK.00700', 'Price': 596.5, 'TradeSide': 'SELL'  
13 [OrderStatus] FILLED_ALL {'Code': 'HK.00700', 'Price': 596.5, 'TradeSide': 'SELL 
```

# Overview

OpenD, which can be runned on your local computer or cloud server, is the gateway program of Futu API. It is responsible for transferring protocol requests to Futu servers and returning the processed data. It is a necessary prerequisite for running Futu API programs. 

OpenD can be runned under 4 operating systems: Windows, MacOS, CentOS and Ubuntu. 

You need to log in to OpenD with your Futu ID (Futubull ID) , Email, Phone number and login password. 

After a successful login into OpenD, the socket service is started for Futu API to connect and communicate. 

# Running Mode

There are 2 modes to run OpenD, you can choose 1 of them below: 

Visualisation OpenD: Provide interface applications, easy to operate, especially suitable for beginners. Please refer to Visualization OpenD for installation and operation. 

Command Line OpenD: Provide command line execution program, which needs to be configured by yourself, which is suitable for users who are familiar with the command line or running on the server for a long time. Please refer to Command Line OpenD for installation and operation. 

# Operation While Running

While OpenD is running, you can view user quota, quote right, connection status, delay statistics, and operate closing API connection, re-login, logging out etc. with Operation Command. 

For more information, please see the following table: 

<table><tr><td>Method</td><td>Visualisation OpenD</td><td>Command Line OpenD</td></tr><tr><td>Direct Method</td><td>through the UI interface</td><td>Send Operation Command through command line</td></tr><tr><td>Indirect 
Medhod</td><td>Send Operation Command 
through Telnet</td><td>Send Operation Command 
through Telnet</td></tr></table>

# Command Line OpenD

# Step 1: Download

Command line OpenD can be runned under 4 operating systems: Windows、MacOS、 CentOS、Ubuntu (Click to download). 

OpenD - Windows 、MacOS 、CentOS 、Ubuntu 

# Step 2: Decompression

Extract the file downloaded in the previous step and find the OpenD configuration file FutuOpenD.xml and the program packaged data file Appdata.dat in the folder. 

FutuOpenD.xml is used to configure the startup parameters of the OpenD program. If it does not exist, the program cannot start correctly. 

Appdata.dat is a large amount of data information the program needs to use, packaging data to reduce the time of downloading data while starting OpenD. If it does not exist, the program can not start correctly. 

Command line OpenD supports user-defined file paths, refer to Command line startup parameters。 

# Step 3: Parameter Configuration

Open and edit the configuration file FutuOpenD.xml as the picture below. For general use, you only need to change your account and login password, and other options can be modified according to the instructions in the following table. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/b0dfcccea774a75f92fc34d8767bc3f1d8fd406672d93d354a4ec5e351f03b25.jpg)


# Configuration item list：

<table><tr><td>Configuration Item</td><td>Description</td></tr><tr><td>ip</td><td>listening address.</td></tr><tr><td>api_port</td><td>API protocol receiving port.</td></tr><tr><td>login_account</td><td>Login account.</td></tr><tr><td>login pwd</td><td>Login password in plaintext.</td></tr><tr><td>login pwd_md5</td><td>Login password ciphertext (32-bit MD5 encrypted hexadecimal).</td></tr><tr><td>Lang</td><td>Language.</td></tr><tr><td>log_level</td><td>Log level of OpenD.</td></tr><tr><td>pushProto_type</td><td>API protocol type.</td></tr><tr><td>qot.push_freqency</td><td>API subscription data push frequency</td></tr><tr><td>telnet_ip</td><td>Remote operation command listening address.</td></tr><tr><td>telnet_port</td><td>Remote operation command listening port.</td></tr><tr><td>rsa_private_key</td><td>API protocol RSA encrypted private key (PKCS#1) file absolute path.</td></tr><tr><td>price Reminder.push</td><td>Whether to receive the price reminder.</td></tr><tr><td>auto_hold-quote_right</td><td>Whether to automatically grab quote right after being kicked.</td></tr><tr><td>future_trade_api_time-zone</td><td>Specify the futures trading API time zone.</td></tr><tr><td>websocket_ip</td><td>WebSocket listening address.</td></tr><tr><td>websocket_port</td><td>WebSocket service listening port.</td></tr><tr><td>websocket_key.md5</td><td>Key ciphertext (32-bit MD5 encrypted hexadecimal).</td></tr><tr><td>websocket_private_key</td><td>WebSocket certificate private key file path.</td></tr><tr><td>websocket_cert</td><td>WebSocket certificate file path.</td></tr><tr><td>pdt_prottection</td><td>Whether to turn on the Pattern Day Trade Protection.</td></tr><tr><td>dtdcall Confirmation</td><td>Whether to turn on the Day-Trading Call Warning.</td></tr></table>

# Tips

To ensure safety of your trading accounts, if the listening address is not local, you must configure a private key to use the trading interface. The quote interface is not subject to this restriction. 

When the WebSocket listening address is not local, you need to configure SSL to start it, and a password should not be set during the certificate private key generation. 

Ciphertext is represented in hexadecimal after plaintext is encrypted by 32-bit MD5, which can be calculated by searching online MD5 encryption (note that there may be a risk of records colliding with libraries calculated through third-party websites) or by downloading MD5 computing tools. The 32-bit MD5 ciphertext is shown in the red box area (e10adc3949ba59abbe56e057f20f883e): 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/fb678184154457790da541169a7e6d94c21fa38b1a4a2d5cac8c3cb28dfabcea.jpg)


Result: 

md5(123456,32) $=$ e10adc3949ba59abbe56e057f20f883e 

md5(123456,16) $\mathbf { \lambda } = \mathbf { \lambda }$ 49ba59abbe56e057 

OpenD reads FutuOpenD.xml in the same directory by default. On MacOS, due to the system protection mechanism, OpenD.app will be assigned a random path at run time, so that the original path can not be found. At this point, there are the following methods: 

Execute fixrun.sh under tar package 

Specify the configuration file path with the command line parameter cfg_file , as described below 

The log level defaults to the info level. During the system development phase, it is not recommended to close the log or modify the log to the warning, error, fatal level to prevent failure to locate problems. 

# Step 4: Command Line Startup

On the command line, change the directory to the folder which FutuOpenD is located, and run the following command to start Command Line FutuOpenD with configuration from FutuOpenD.xml. 

Windows： FutuOpenD 

Linux： ./FutuOpenD 

MacOS： ./FutuOpenD.app/Contents/MacOS/FutuOpenD 

N Command Line Startup Parameters 

If the same parameters exist on both the command line and the configuration file, the command line parameters take precedence. For details of the parameters, please see the following table: 

<table><tr><td>Configuration Item</td><td>Description</td></tr><tr><td>login_account</td><td>Login account.</td></tr><tr><td>login pwd</td><td>Plaintext of login password.</td></tr><tr><td>login pwd_md5</td><td>Login password ciphertext (32-bit MD5 encrypted hexadecimal).</td></tr><tr><td>cfg_file</td><td>The absolute path of OpenD configuration file.</td></tr><tr><td>console</td><td>Whether to display the console.</td></tr><tr><td>lang</td><td>OpenD language.</td></tr><tr><td>api_ip</td><td>API service listening address.</td></tr><tr><td>api_port</td><td>API listening port.</td></tr><tr><td>help</td><td>Output startup command line parameters and exit the program.</td></tr><tr><td>log_level</td><td>Log level of OpenD.</td></tr><tr><td>no_monitor</td><td>Whether to start the daemon.</td></tr><tr><td>websocket_ip</td><td>WebSocket listening address.</td></tr><tr><td>websocket_port</td><td>WebSocket service listening port.</td></tr><tr><td>websocket_private_key</td><td>WebSocket certificate private key file path.</td></tr><tr><td>websocket_cert</td><td>WebSocket certificate file path.</td></tr><tr><td>websocket_key_md5</td><td>Key ciphertext (32-bit MD5 encrypted hexadecimal).</td></tr><tr><td>price Reminder.push</td><td>Whether to receive the price reminder.</td></tr><tr><td>auto_hold-quote_right</td><td>Whether to automatically grab quote right after being kicked.</td></tr><tr><td>future_trade api_time-zone</td><td>Specify the futures Trade API time zone.</td></tr></table>

# Operation Command

You can do operate OpenD by sending Operation Command from the command line or Telent. 

Command format: cmd -param_key1=param_value1 -param_key2=param_value2 

Using the following example to describe how to use Telnet: help -cmd=exit 

1. Configure Telnet address and Telnet port in the OpenD set up parameter. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/e73436e63e3992a45a97e50e285c4456262468cef95c261ea02449c259d58787.jpg)


# Futu OpenD Login

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/4e1763f7520b317ecb6915080a728ad6f9fd5ad864d771bbae919e153fee0e82.jpg)


Remember Me 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/4f8ae217a2b98946d198c333309d3ec33eff5fe5f25406e4424e674cfac23106.jpg)


# Basic

# Advanced


Futu0penD.xm1区


```txt
1 <futu_open>   
2 <-- 基础参数 -->   
3 <-- Basic parameters -->   
4 <-- 协议监听地址，不填默认127.0.0.1 -->   
5 <-- Listening address. 127.0.0.1 if not specified --> // Listening address. 127.0.0.1 by default   
6 <ip>127.0.0.1</ip>   
7 <-- API接口协议监听端口 -->   
8 <-- API interface protocol listening port -->   
9 <api_port>11111</api_port>   
10 <-- 登录帐号 -->   
11 <login_account>100000</login_account>   
12 <-- 登录密码32位MD5加密16进制 -->   
13 <-- <login pwd md5>6e55f158a827blalc432la245aaaad88</login pwd md5> -->   
14 <-- 登录密码明文，密码密文存在情况下只使用密文 -->   
15 <login pwd>123456</login pwd>   
16 <-- FutuOpenD语言，en：英文，chs：简体中文 -->   
17 <lang>chs</lang>   
18 <-- 进阶参数 -->   
19 <-- Advanced parameters -->   
20 <-- FutuOpenD日志等级，no,debug,info,warning,error,fatal -->   
21 <log_level>info</log_level>   
22 <-- API推送协议格式，0:pb，l:json -->   
23 <-- API push protocol format，0:pb，l:json -->   
24 <push proto_type>0</push proto_type>   
25 <-- API订阅数据推送频率控制，单位毫秒，目前不包括K线和分时，不设置则不限制频率-->   
26 <-- API subscription data push frequency control, in milliseconds, currently does not include K-line and time-sharing, if not   
27 <--<poriousness>1000</poriousness> -->   
28 <-- Telnet监听地址，不填默认127.0.0.1 -->   
29 <-- Telnet listening address, default 127.0.0.1 if not filled in --> // Telnet listening address, 127.0.0.1 by default   
30 <telnet_ip>127.0.0.1</telnet_ip>   
31 <-- Telnet监听端口 -->   
32 <-- Telnet listening port -->   
33 <telnet port>22222</telnet port>   
34 <-- API协议加密私钥文件路径，不设置则不加密 -->   
35 <-- API protocol encrypted private key file path, if not set, it will not be encrypted --> // File path for private key for   
36 <-- <rsa_private_key>D:\rsa</rsa_private_key> -->   
37 <-- 是否接收到价提醒推送，0：不接收，1：接收 -->   
38 <-- Whether to receive the price reminder push, 0: not receive, 1: receive -->
```

2. Start OpenD (it will also start Telnet). 

3. Via Telnet，send the command help -cmd=exit to OpenD。 

```python
1 from telnetlib import Telnet
2 with Telnet('127.0.0.1', 22222) as tn: # Telnet address is: 127.0.0.1, Telnet port
3 tn.write(b'help -cmd=exit\r\n')
4 reply = b''
5 while True:
6 msg = tn.read_until(b'\r\n', timeout=0.5)
7 reply += msg
8 if msg == b': break
9 print-replydecode('gb2312')) 
```

# Command Help

help -cmd=exit 

View the detailed information of the specified command, output the command list if no parameter is specified 

Parameters: 

cmd: command 

# Exit the Program

Exit 

Exit OpenD 

# Request Mobile Phone Verification Code

req_phone_verify_code 

Requested mobile phone verification code. Security verification is required when the device lock is enabled and the device is logged in at the first time. 

. Frequency limitations: 

Maximal 1 request every 60 seconds 

# Enter the Phone Verification Code

Input_phone_verify_code -code=123456 

Enter the phone verification code and continue the login process. 

. Parameters: 

code: mobile phone verification code 

. Frequency limitations: 

Maximal 10 requests every 60 seconds 

# Request Graphic Verification Code

req_pic_verify_code 

Request a graphic verification code. When you enter the wrong login password multiple times, you need to enter the graphic verification code. 

. Frequency limitations: 

Maximal 10 requests every 60 seconds 

# Enter Graphic Verification Code

Input_pic_verify_code -code=1234 

Enter the graphic verification code and continue the login process. 

. Parameters: 

code: Graphic verification code 

. Frequency limitations: 

Maximal 10 requests every 60 seconds 

# Relogin

relogin -login_pwd=123456 

This command can be used when the user is required to log in again when the login password is changed or the device lock is opened midway. You can only relogin to the current account, and changing accounts is not supported. The password parameter is mainly used to the situation that the login password had been modified. If login_pwd is not set, the login password at startup will be used. 

? Parameters: 

login_pwd: login password in plaintext 

login_pwd_md5: login password in ciphertext (32-bit MD5 encrypted hexadecimal) 

Frequency limitations: 

Maximal 10 requests every hour 

# Time Delay Between Detection and Connection Point

ping 

Delay before detection and connection point 

Frequency limitations: 

Maximal 10 requests every 60 seconds 

# Display Delay Statistics Report

show_delay_report -detail_report_path=D:/detail.txt -push_count_type=sr2cs 

Display delay statistics report, including push delay, request delay and order delay. Data is cleaned up at 6:00 Beijing time every day. 

. Parameters: 

detail_report_path: file output path (MAC system only supports absolute path, not relative path), optional parameter, if not specified, output to the console 

push_count_type: the type of push delay (sr2ss, ss2cr, cr2cs, ss2cs, sr2cs), sr2cs by default. 

sr refers to the server receiving time (currently only HK stocks support this time) 

ss refers to the server sending time 

cr refers to OpenD receiving time 

cs refers to OpenD sending time 

# Close API Connection

close_api_conn -conn_id=123456 

Close an API connection, if not specified, close all connections 

. Parameters: 

conn_id: API connection ID 

# Show Subscription Status

show_sub_info -conn_id=123456 -sub_info_path=D:/detail.txt 

Display the subscription status of a connection, if not specified, display all connections 

Parameters: 

conn_id: API connection ID 

sub_info_path: file output path (MAC system only supports absolute path, not relative path), optional parameter, if not specified, output to the console 

# Request the Highest Quotation Permission

request_highest_quote_right 

When the advanced quotation authority is occupied by other devices (such as desktop/mobile terminal), you can use this command to request the highest quotation authority again (And then, other devices that are logged in will not be able to use advanced quote). 

. Frequency limitations: 

Maximal 10 requests every 60 seconds 

# Update

update 

Update 


Overview


<table><tr><td colspan="2">Module</td><td>Interface Name</td><td>Function Description</td></tr><tr><td rowspan="16">Real-time Data</td><td rowspan="4">Subscription</td><td>subscribe</td><td>Subscribe real-time market data</td></tr><tr><td>unsubscribe</td><td>Unsubscribe subscriptions</td></tr><tr><td>unsubscribe_all</td><td>Unsubscribe all subscriptions</td></tr><tr><td>query Subscription</td><td>Get subscription information</td></tr><tr><td rowspan="6">Push and Callback</td><td>StockQuoteHandlerBase</td><td>Real-time quote callback</td></tr><tr><td>OrderBookHandlerBase</td><td>Real-time order book callback</td></tr><tr><td>CurKlineHandlerBase</td><td>Real-time candlestick callback</td></tr><tr><td>TickerHandlerBase</td><td>Real-time tick-by-tick callback</td></tr><tr><td>RTDataHandlerBase</td><td>Real-time time frame callback</td></tr><tr><td>BrokerHandlerBase</td><td>Real-time broker queue callback</td></tr><tr><td rowspan="6">Get</td><td>get_market_snapshot</td><td>Get market snapshot</td></tr><tr><td>get_stockQuote</td><td>Get real-time quote</td></tr><tr><td>get_order_book</td><td>Get real-time order book</td></tr><tr><td>get.cur_kline</td><td>Get real-time candlestick</td></tr><tr><td>get_rt_data</td><td>Get real-time time frame data</td></tr><tr><td>get_rt-ticketer</td><td>Get real-time tick-by-tick</td></tr><tr><td></td><td></td><td>get_broker_queue</td><td>Get real-time broker queue</td></tr><tr><td colspan="2" rowspan="6">Basic Data</td><td>get_market_state</td><td>Get market status of securities</td></tr><tr><td>get_capital_flow</td><td>Get capital flow</td></tr><tr><td>get_capital_distribution</td><td>Get capital distribution</td></tr><tr><td>get-ownerplate</td><td>Get the stock ownership plate</td></tr><tr><td>request_history_kline</td><td>Get historical candlesticks</td></tr><tr><td>get_rehab</td><td>Get the stock adjustment factor</td></tr><tr><td colspan="2" rowspan="5">Related Derivatives</td><td>get_option_expiration_date</td><td>Query all expiration dates of option chains through the underlying stock.</td></tr><tr><td>get_option_chain</td><td>Get the option chain from an underlying stock</td></tr><tr><td>get_warrant</td><td>Get filtered warrant (for HK market only)</td></tr><tr><td>get.Referenceestoock_list</td><td>Get related data of securities</td></tr><tr><td>get_future_info</td><td>Get futures contract information</td></tr><tr><td colspan="2" rowspan="6">Market Filter</td><td>get_stock_filter</td><td>Filter stocks by condition</td></tr><tr><td>get_plate_stock</td><td>Get the list of stocks in the plate</td></tr><tr><td>get_plate_list</td><td>Get plate list</td></tr><tr><td>get_stockbasicinfo</td><td>Get stock basic information</td></tr><tr><td>get IPO_list</td><td>Get IPO information of a specific market</td></tr><tr><td>get_global_state</td><td>Get global status</td></tr></table>

<table><tr><td></td><td>request_trading_day</td><td>Get trading calendar</td></tr><tr><td rowspan="7">Customization</td><td>get_history_kl_quota</td><td>Get usage details of historical candlestick quota</td></tr><tr><td>set_price Reminder</td><td>Add, delete, modify, enable, and disable price reminders for specified stocks</td></tr><tr><td>get_price Reminder</td><td>Get a list of price reminders set for the specified stock or market</td></tr><tr><td>get_user_security_group</td><td>Get a list of groups from the user watchlist</td></tr><tr><td>get_user_security</td><td>Get a list of a specified group from watchlist</td></tr><tr><td>modify_user_security</td><td>Modify the specific group from the watchlist</td></tr><tr><td>PriceReminderHandlerBase</td><td>The price reminder notification callback</td></tr></table>

# Quote Object

# Create and Initialize the Connection

OpenQuoteContext(host='127.0.0.1', port=11111, is_encrypt=None) 

. Introduction 

Create and initialize market connection 

Parameters 

Parameter|Type|Description ??:-|:- host|str|OpenD listening address. port|int|OpenD listening port. is_encrypt|bool|Whether to enable encryption. 

Example 

from futu import * 

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111, is_encrypt=False) 

quote_ctx.close() # After using the connection, remember to close it to prevent 

# Close Connection

# close()

. Introduction 

Close the interface quotation object. By default, the threads created inside the Futu API will prevent the process from exiting, and the process can exit normally only after all Contexts are closed. But through set_all_thread_daemon, all internal threads can be set as daemon threads. 

At this time, even if the close of Context is not called, the process can exit normally. 

Example 

from futu import * 

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111) 

# Start-up

start() 

. Introduction 

Start to receive push data asynchronously 

# Stop

stop() 

Introduction 

Stop receiving push data asynchronously 

# Subscribe and Unsubscribe

# Subscribe to Real-Time Market Data

subscribe(code_list, subtype_list, is_first_push=True, subscribe_push=True, is_detailed_orderbook $\cdot$ False, extended_time=False, session=Session.NONE) 

# . Description

To subscribe to the real-time information required for registration, specify the stock and subscription data types. 

HK market (including underlying stocks, warrants, CBBCs, options, futures) subscriptions require LV1 and above permissions. Subscriptions are not supported under BMP permissions. 

US market (including underlying stocks, ETFs) subscriptions for overnight quotes require LV1 and above permissions. Subscriptions are not supported under BMP permissions. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>A list of stock codes that need to be subscribed.</td></tr><tr><td>subtype_list</td><td>list</td><td>List of data types that need to be subscribed.</td></tr><tr><td>is_first.push</td><td>bool</td><td>Whether to push the cached data immediately after a successful subscription.</td></tr><tr><td>subscribe.push</td><td>bool</td><td>Whether to push data after subscription.</td></tr><tr><td>isDetailed_orderbook</td><td>bool</td><td>Whether to subscribe to the detailed order book.</td></tr><tr><td>extended_time</td><td>bool</td><td>Whether to allow pre-market and after-hours data of US stocks.</td></tr><tr><td>session</td><td>Session</td><td>US stocks quotes session</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">err_message</td><td>NONE</td><td>If ret == RET_OK, None is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Example 

1 import time   
2 from futu import \*   
3 class OrderBookTest(OrderBookHandlerBase):   
4 def on_recv_rsp(self, rsp_pb):   
5 ret_code,data $=$ super(OrderBookTest,self).on_recv_rsp(rsp_pb)   
6 if ret_code != RET_OK:   
7 print("OrderBookTest: error, msg: $\% s$ \% data)   
8 return RET_ERROR, data   
9 print("OrderBookTest ",data)# OrderBookTest's own processing logic   
10 return RET_OK, data   
11 quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 12 handler $=$ OrderBookTest()   
13 quoteCtx.sethandler(handle)# Set real-time swing callback   
14 quoteCtx.subscribe([US.AAPL],[SubType.ORDER.Book]) # Subscribe to the order   
15 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
16 quoteCtx.close() # Close the current link, OpenD will automatically cancel the 

Output 

```txt
1 OrderBookTest{'code': 'US.AAPL', 'name': 'Apple', 'svr_recv_time_bid': '2025-04 
```

Cancel Market Data Subscription 

unsubscribe(code_list, subtype_list, unsubscribe_all=False) 

. Description 

unsubscribe 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>A list of stock codes to unsubscribe.</td></tr><tr><td>subtype_list</td><td>list</td><td>List of data types that need to be subscribed.</td></tr><tr><td>unsubscribe_all</td><td>bool</td><td>Cancel all subscriptions.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">err_message</td><td>NONE</td><td>If ret == RET_OK, None is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

. Example 

1 from futu import \*   
2 import time   
3 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111)   
4   
5 print('current subscription status：'，quoteCtx.requestsubscription()）#Query the   
6 ret_sub, err_message $=$ quoteCtx subscribing(['US.AAPL']，[SubType.QUOTE，SubType.]   
7 #First subscribed to the two types of QUOTE and TICKER.After the subscription   
8 if ret_sub $= =$ RET_OK:#Subscription successful   
9 print('subscribe successfully! current subscription status：'，quoteCtx.que   
10 time.sleep(60)#You can unsubscribe at least 1 minute after subscribing   
11 ret_unsub, err_message_unsub $=$ quoteCtx.Unsubscribe(['US.AAPL'], [SubType.QU   
12 if ret_unsub $= =$ RET_OK:   
13 print('unsubscribe successfully! current subscription status：',quoteCtx   
14 else: 

```python
print('unsubscription failed!', err_message_unsub)   
else: print('subscription failed', err_message) quotectx.close() # After using the connection, remember to close it to prevent 
```

# Output

```txt
current subscription status : (0,{'total_used': 0,'remain': 1000,'own_used': 0)  
subscribe successfully! current subscription status : (0,{'total_used': 2,'remain': 1}  
unsubscribe successfully! current subscription status: (0,{'total_used': 1,'rem 
```

# Cancel All Market Data Subscriptions

```txt
unsubscribe_all() 
```

. Description 

Unsubscribe all subscriptions 

. Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">err_message</td><td>NONE</td><td>If ret == RET_OK, None is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

. Example 

1 from futu import \*   
2 import time   
3 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111)   
4   
5 print('current subscription status：'，quoteCtx(querysubscription())#Query the   
6 ret_sub,err_message $=$ quoteCtx subscribing['US.AAPL']，[SubType.QUOTE，SubType.T   
7 #First subscribed to the two types of QUOTE and TICKER.After the subscription   
8 ifret_sub $= =$ RET_OK:#Subscription successful 

```python
print('subscribe successfully! current subscription status: ', quoteCtx.quen  
time.sleep(60) # You can unsubscribe at least 1 minute after subscribing  
ret_unsub, err_message_unsub = quoteCtx.Unsubscribe_all() # Cancel all subse  
if ret_unsub == RET_OK:  
    print('subscribe all successfully! current subscription status: ', quote  
else:  
    print('Failed to cancel all subscriptions! ', err_message_unsub)  
else:  
    print('subscription failed', err_message)  
quoteCtx.close() # After using the connection, remember to close it to prevent 
```

# . Output

```txt
current subscription status : (0,{'total_used': 0,'remain': 1000,'own_used': 0)  
subscribe successfully! current subscription status : (0,{'total_used': 2,'remain': 0)  
unsubscribe all successfully! current subscription status: (0,{'total_used': 0, 
```

# Interface Limitations

Supports subscriptions of multiple real-time data types, refer to SubType, each stock subscription for one one quota. 

Please refer to Subscription Quota & Historical Candlestick Quota for Subscription Quota rules. 

You can unsubscribe after subscribing after at least one minute. 

Due to the large amount of SF market data in Hong Kong stocks, in order to ensure the speed of the SF market and the processing performance of OpenD, currently SF authorized users are limited to subscribing to 50 security products (including hkex stocks, warrants, bulls and bears) at the same time, the remaining subscription quota can still be used to subscribe to other types, such as: tickers and brokerage etc. 

HK options and futures do not support subscription to TICKER type under LV1 authority. 

# Get Subscription Status

query_subscription(is_all_conn=True) 

Description 

Get subscription information 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>is_allconn</td><td>bool</td><td>Whether to return the subscription status of all connections.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>dict</td><td>If ret == RET_OK, subscription information data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

subscription information data format as follows: 

```python
{ 'total_used': subscription quota used by all connections, 'own_used': The subscription quota used by the current connection, 'remain': remaining subscription quota, 'sub_list': The stock list corresponding to each subscription type, { 'Subscription type': A list of all subscribed stocks under this subscript } } 
```


. Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 3 quoteCtx.subscribe([HK.00700],[SubType.QUOTE])   
5 ret, data $=$ quoteCtx.querysubscription()   
6 if ret $= =$ RET_OK: print(data)   
8 else: print('error:',data)   
10 quoteCtx.close() # After using the connection, remember to close it to prevent 


? Output


```python
1 {'total_used': 1, 'remain': 999, 'own_used': 1, 'sub_list': {'QUOTE': ['HK.00700 
```

# Real-time Quote Callback

on_recv_rsp(self, rsp_pb) 

# Description

Real-time quotation callback, asynchronous processing of real-time quotation push of subscribed stocks. After receiving the real-time quote data push, it will call back to this function. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdateBasicQot_pb2.Response</td><td>This parameter does not need to be processed in the derived class.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, quotation data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

quotation data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>data_date</td><td>str</td><td>Date.</td></tr><tr><td>data_time</td><td>str</td><td>Time of latest price.</td></tr><tr><td>last_price</td><td>float</td><td>Latest price.</td></tr><tr><td>open_price</td><td>float</td><td>Open.</td></tr><tr><td>high_price</td><td>float</td><td>High.</td></tr><tr><td>low_price</td><td>float</td><td>Low.</td></tr><tr><td>prev_close_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>amplitude</td><td>int</td><td>Amplitude.</td></tr><tr><td>suspension</td><td>bool</td><td>Whether trading is suspended.</td></tr><tr><td>listing_date</td><td>str</td><td>Listing date.</td></tr><tr><td>price_spread</td><td>float</td><td>Spread.</td></tr><tr><td>dark_status</td><td>DarkStatus</td><td>Grey market transaction status.</td></tr><tr><td>sec_status</td><td>SecurityStatus</td><td>Stock status.</td></tr><tr><td>strike_price</td><td>float</td><td>Strike price.</td></tr><tr><td>contract_size</td><td>float</td><td>Contract size.</td></tr><tr><td>open_interest</td><td>int</td><td>Number of open positions.</td></tr><tr><td>implied_volatility</td><td>float</td><td>Implied volatility.</td></tr><tr><td>premium</td><td>float</td><td>Premium.</td></tr><tr><td>delta</td><td>float</td><td>Greek value Delta.</td></tr><tr><td>gamma</td><td>float</td><td>Greek value Gamma.</td></tr><tr><td>vega</td><td>float</td><td>Greek value Vega.</td></tr><tr><td>theta</td><td>float</td><td>Greek value Theta.</td></tr><tr><td>rho</td><td>float</td><td>Greek value Rho.</td></tr><tr><td>index_option_type</td><td>IndexOptionType</td><td>Index option type.</td></tr><tr><td>net_open_interest</td><td>int</td><td>Net open contract number.</td></tr><tr><td>expiration_date_distance</td><td>int</td><td>The number of days from the expiry date.</td></tr><tr><td>contract_nominal_value</td><td>float</td><td>Contract nominal amount.</td></tr><tr><td>owner LOT multiplier</td><td>float</td><td>Equal number of underlying stocks.</td></tr><tr><td>option_area_type</td><td>OptionAreaType</td><td>Option type (by exercise time).</td></tr><tr><td>contract-multiplier</td><td>float</td><td>Contract multiplier.</td></tr><tr><td>pre_price</td><td>float</td><td>Pre-market price.</td></tr><tr><td>pre_high_price</td><td>float</td><td>Pre-market high.</td></tr><tr><td>pre_low_price</td><td>float</td><td>Pre-market low.</td></tr><tr><td>pre_volume</td><td>int</td><td>Pre-market volume.</td></tr><tr><td>pre_turnover</td><td>float</td><td>Pre-market turnover.</td></tr><tr><td>pre_change_val</td><td>float</td><td>Pre-market change.</td></tr><tr><td>pre_change_rate</td><td>float</td><td>Pre-market change rate.</td></tr><tr><td>pre_amplitude</td><td>float</td><td>Pre-market amplitude.</td></tr><tr><td>after_price</td><td>float</td><td>After-hours price.</td></tr><tr><td>after_high_price</td><td>float</td><td>After-hours high.</td></tr><tr><td>after_low_price</td><td>float</td><td>After-hours low.</td></tr><tr><td>after_volume</td><td>int</td><td>After-hours volume.</td></tr><tr><td>After_turnover</td><td>float</td><td>After-hours turnover.</td></tr><tr><td>after_change_val</td><td>float</td><td>After-hours change.</td></tr><tr><td>after_change_rate</td><td>float</td><td>After-hours change rate.</td></tr><tr><td>after_amplitude</td><td>float</td><td>After-hours amplitude.</td></tr><tr><td>overnight_price</td><td>float</td><td>Overnight price.</td></tr><tr><td>overnight_high_price</td><td>float</td><td>Overnight high.</td></tr><tr><td>overnight_low_price</td><td>float</td><td>Overnight low.</td></tr><tr><td>overnight_volume</td><td>int</td><td>Overnight volume.</td></tr><tr><td>overnight_turnover</td><td>float</td><td>Overnight turnover.</td></tr><tr><td>overnight_change_val</td><td>float</td><td>Overnight change.</td></tr><tr><td>overnight_change_rate</td><td>float</td><td>Overnight change rate.</td></tr><tr><td>overnight_amplitude</td><td>float</td><td>Overnight amplitude.</td></tr><tr><td>last_settle_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>position</td><td>float</td><td>Holding position.</td></tr><tr><td>position_change</td><td>float</td><td>Daily position change.</td></tr></table>


. Example


1 import time   
2 from futu import \*   
3   
4 class StockQuoteTest(StockQuoteHandlerBase):   
5 def on_recv_rsp(self, rsp_cb):   
6 ret_code，data $=$ super(StockQuoteTest,self).on_recv_rsp(rsp_cb)   
7 if ret_code != RET_OK:   
8 print("StockQuoteTest: error，msg:%s"% data)   
9 return RET_ERROR，data   
10 print("StockQuoteTest"，data)#StockQuoteTest's own processing logic   
11 return RET_OK，data   
12 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
13 handler $=$ StockQuoteTest()   
14 quoteCtx.sethandler(handle)#Setreal-timequote callback   
15 ret，data $=$ quoteCtx.subscribe(['US.AAPL']，[SubType.QUOTE]）#Subscribe to the   
16 ifret $= =$ RET_OK:   
17 print(data)   
18 else:   
19 print('error：',data)   
20 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
21 quoteCtx.close() # Close the current link，OpenD will automatically cancel the 


Output


```perl
1 StockQuoteTest code name data_date data_time last_price open_price high 2 US.AAPL Apple 0.0 0.0 0.0 
```

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Real-time Quote of Securities API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

# Real-time Order Book Callback

on_recv_rsp(self, rsp_pb) 

# Description

Real-time quotation callback, asynchronous processing of real-time quotation push of subscribed stocks. It will call back to this function after receiving the push of real-time disk data. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdateOrderBook_pb2.Response</td><td>This parameter does not need to be processed directly in the derived class.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>dict</td><td>If ret == RET_OK, plate data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Order Book format as follows： 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>svr_recv_timebid</td><td>str</td><td>The time when Futu server receives order book of bid from the exchange.</td></tr><tr><td>svr_recv_time Asking</td><td>str</td><td>The time when Futu server receives order book of ask from the exchange.</td></tr><tr><td>Bid</td><td>list</td><td>Each tuple contains the following information: Bid price, bid volume, order qty of bid, order details of bid.</td></tr><tr><td>Ask</td><td>list</td><td>Each tuple contains the following information: Ask price, ask volume, order qty of ask, order details of ask.</td></tr></table>

The format of Bid and Ask fields as follows： 

```txt
'Bid': [ (bid_price1, bid_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num 
```


Example


1 import time   
2 from futu import \*   
3 class OrderBookTest(OrderBookHandlerBase):   
4 def on_recv_rsp(self, rsp_pb):   
5 ret_code,data $=$ super(OrderBookTest,self).on_recv_rsp(rsp_pb)   
6 if ret_code != RET_OK:   
7 print("OrderBookTest: error, msg: $\% s$ % data)   
8 return RET_ERROR, data   
9 print("OrderBookTest ",data)# OrderBookTest's own processing logic   
10 return RET_OK, data   
11 quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 12 handler $=$ OrderBookTest()   
13 quoteCtx.sethandler(handle)# Set real-time swing callback   
14 ret,data $=$ quoteCtx.subscribe([US.AAPL],[SubType.ORDERSK]) # Subscribe ta   
15 if ret $= =$ RET_OK:   
16 print(data)   
17 else: 

```txt
print('error: ', data) time.sleep(15) # Set the script to receive OpenD push duration to 15 seconds quotectx.close() # Close the current link, OpenD will automatically cancel the 
```

# Output

```python
1 OrderBookTest {'code': 'US.AAPL', 'name': 'Apple', 'svr_recv_time_bid': '', 'svr 
```

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Real-time Orderbook API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

Real-time order book callback for US stocks, will continuously update data during the current trading session, with no need to set the session parameter. 

# Real-time Candlestick Callback

on_recv_rsp(self, rsp_pb) 

# Description

Real-time candlestick callback, asynchronous processing of real-time candlestick push for subscribed stocks. 

After receiving real-time candlestick data push, it will call back to this function. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdateKL_pb2.Response</td><td>This parameter does not need to be processed directly in the derived class.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, IPO data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

IPO data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>time_key</td><td>str</td><td>Time.</td></tr><tr><td>open</td><td>float</td><td>Open.</td></tr><tr><td>close</td><td>float</td><td>Close.</td></tr><tr><td>high</td><td>float</td><td>High.</td></tr><tr><td>low</td><td>float</td><td>Low.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>pe_ratio</td><td>float</td><td>P/E ratio.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>last_close</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>k_type</td><td>KLTType</td><td>Candlestick type.</td></tr></table>

# Example

1 import time   
2 from futu import \*   
3 class CurKlineTest(CurKlineHandlerBase):   
4 def on_recv_rsp(self, rsp_pb):   
5 ret_code，data $=$ super(CurKlineTest,self).on_recv_rsp(rsp_pb)   
6 if ret_code != RET_OK:   
7 print("CurKlineTest: error，msg:%s"% data)   
8 return RET_ERROR, data   
9 print("CurKlineTest ", data) # CurKlineTest's own processing logic   
10 return RET_OK, data   
11 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
12 handler $=$ CurKlineTest()   
13 quoteCtx.sethandlerhandler)# Set real-time candlestick callback   
14 ret，data $=$ quoteCtx.subscribe(['US.AAPL']，[SubType.K_1M]，session=Session.ALL)   
15 if ret $= =$ RET_OK:   
16 print(data) 

```txt
17 else:  
18 print('error: ', data)  
19 time.sleep(15) # Set the script to receive OpenD push duration to 15 seconds  
20 quotectx.close() # Close the current link, OpenD will automatically cancel the 
```


Output


```csv
1 CurKlineTest code name time_key open close high low 2 US.AAPL APPLE 2025-04-07 05:15:00 180.39 180.26 180.46 180.2 1322 
```

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Real-time Candlestick API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

Options related candlestick data, only supports 1 day, 1 minute, 5 minutes, 15 minutes and 60 minutes. 

# Real-time Time Frame Callback

on_recv_rsp(self, rsp_pb) 

# Description

Real-time Time Frame callback, asynchronous processing of real-time Time Frame push of subscribed stocks. After receiving the real-time Time Frame data push, it will call back to this function. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdateRT_pb2.Response</td><td>This parameter does not need to be processed directly in the derived class.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, Time Frame data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Time Frame data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>time</td><td>str</td><td>Time.</td></tr><tr><td>is_blank</td><td>bool</td><td>Data status.</td></tr><tr><td>opened_mins</td><td>int</td><td>How many minutes have passed from 0 o'clock.</td></tr><tr><td>cur_price</td><td>float</td><td>Current price.</td></tr><tr><td>last_close</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>avg_price</td><td>float</td><td>Average price.</td></tr><tr><td>volume</td><td>float</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Transaction amount.</td></tr></table>


Example


1 import time   
2 from futu import \*   
3   
4 class RTDataTest(RTDataHandlerBase):   
5 def on_recv_rsp(self, rsp_pb):   
6 ret_code，data $=$ super(RTDataTest,self).on_recv_rsp(rsp_pb)   
7 if ret_code != RET_OK:   
8 print("RTDataTest: error，msg:%s"%data)   
9 return RET_ERROR, data   
10 print("RTDataTest ",data)#RTDataTest's own processing logic   
11 return RET_OK，data   
12 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
13 handler $=$ RTDataTest()   
14 quoteCtx.sethandlerhandler)#Set real-time Time Frame push callback   
15 ret，data $=$ quoteCtx subscribing(['US.AAPL']，[SubType.RT_DATA]，session=Session.A   
16 if ret $= =$ RET_OK:   
17 print(data)   
18 else:   
19 print('error:'，data)   
20 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
21 quoteCtx.close() # Close the current link, OpenD will automatically cancel the 

Output 

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Real-time Time Frame Data API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

# Real-time Tick-by-Tick Callback

on_recv_rsp(self, rsp_pb) 

# Description

Real-time callback, asynchronously processing the real-time push of subscribed stocks. After receiving real-time data push, it will call back to this function. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdateTicker_pb2.Response</td><td>This parameter does not need to be processed directly in the derived class.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, tick-by-tick data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Tick-by-tick data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>sequence</td><td>int</td><td>Sequence number.</td></tr><tr><td>time</td><td>str</td><td>Transaction time.</td></tr><tr><td>price</td><td>float</td><td>Transaction price.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Transaction amount.</td></tr><tr><td>ticket_direction</td><td>TickerDirect</td><td>Tick-By-Tick direction.</td></tr><tr><td>type</td><td>TickerType</td><td>Tick-By-Tick type.</td></tr><tr><td>push_data_type</td><td>PushDataType</td><td>Source of data.</td></tr></table>


Example


1 import time   
2 from futu import \*   
3   
4 class TickerTest(TickerHandlerBase):   
5 def on_recv_rsp(self, rsp Pb):   
6 ret_code，data $=$ super(TickerTest,self).on_recv_rsp(rsp_pb)   
7 if ret_code != RET_OK:   
8 print("TickerTest: error，msg:%s"%data)   
9 return RET_ERROR, data   
10 print("TickerTest ",data)#TickerTest's own processing logic   
11 return RET_OK，data   
12 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111)   
13 handler $=$ TickerTest()   
14 quoteCtx.sethandlerhandler)#Set real-time push callback   
15 ret，data $=$ quoteCtx.subscribe(['US.AAPL']，[SubType.TICKER]，session=Session.A   
16 if ret $= =$ RET_OK:   
17 print(data)   
18 else:   
19 print('error:'，data)   
20 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
21 quoteCtx.close() # Close the current link, OpenD will automatically cancel the 

Output 

TickerTest code name 

0 US.AAPL APPLE 2025-04-07 05:25:44.116 

time 

179.81 

price 

volume 

1618.29 

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Real-time Tick-By-Tick API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

After the market connection is reconnected, during the disconnected period of OpenD pulls, the nearest (up to 50) Tick-By-Tick data is pushed, which can be distinguished by the Tick-By-Tick push type field 

# Real-time Broker Queue Callback

on_recv_rsp(self, rsp_pb) 

# Description

Real-time broker queue callback, asynchronous processing of real-time broker queue push of subscribed stocks. After receiving the real-time broker queue data push, it will call back to this function. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdateBroker_pb2.Response</td><td>This parameter does not need to be processed directly in the derived class.</td></tr></table>

# . Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>tuple</td><td>If ret == RET_OK, broker queue data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Broker queue data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_code</td><td>str</td><td>Stock code.</td></tr><tr><td>bid_frame_table</td><td>pd.DataFrame</td><td>Data from bid.</td></tr><tr><td>ask_frame_table</td><td>pd.DataFrame</td><td>Data from ask.</td></tr></table>

Bid_frame_table format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>bid_broker_id</td><td>int</td><td>Bid broker ID.</td></tr><tr><td>bid_broker_name</td><td>str</td><td>Bid broker name.</td></tr><tr><td>bid_broker_pos</td><td>int</td><td>Broker level.</td></tr><tr><td>order_id</td><td>int</td><td>Exchange order ID.</td></tr><tr><td>order_volume</td><td>int</td><td>Order volume.</td></tr></table>

Ask_frame_table format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>ask_broker_id</td><td>int</td><td>Ask Broker ID.</td></tr><tr><td>ask_broker_name</td><td>str</td><td>Ask Broker name.</td></tr><tr><td>ask_broker_pos</td><td>int</td><td>Broker level.</td></tr><tr><td>order_id</td><td>int</td><td>Exchange order ID.</td></tr><tr><td>order_volume</td><td>int</td><td>Order volume.</td></tr></table>

. Example 

import time from futu import * 

4 class BrokerTest(BrokerHandlerBase):   
5 def on_recv_rsp(self, rsp_pb):   
6 ret_code，err_or_stock_code，data $=$ super(BrokerTest,self).on_recv_rsp(   
7 if ret_code $! =$ RET_OK:   
8 print("BrokerTest: error，msg:{}.format(err_or_stock_code))   
9 return RET_ERROR, data   
10 print("BrokerTest: stock:{} data:{} ".format(err_or_stock_code，data))   
11 return RET_OK, data   
12 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
13 handler $=$ BrokerTest()   
14 quoteCtx.sethandler(handle)# Set real-time broker push callback   
15 ret，data $=$ quoteCtx.subscribe(['HK.00700']，[SubType.BROKER]) # Subscribe to the   
16 if ret $= =$ RET_OK:   
17 print(data)   
18 else:   
19 print('error:'，data)   
20 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
21 quoteCtx.close() # Close the current link，OpenD will automatically cancel the 


. Output


```txt
BrokerTest: stock: HK.00700 data: [ code name bid_broker_id 2 HK.00700 TENCENT 5338 J.P. Morgan Broking (Hong Kong) 3 ... ... ... ... 4 36 HK.00700 TENCENT 8305 Futu Securities International (Hong Kong) 5 [37 rows x 7 columns], code name ask_broker_id 7 HK.00700 TENCENT 1179 Huatai Financial Holdings (Hong Kong) Limit 8 ... ... ... ... ... 9 39 HK.00700 TENCENT 6996 China Investment Information Services Limit 10 [40 rows x 7 columns]] 
```

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Real-time Orderbook API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

Under the BMP & LV1 HK market quotes, the broker queue market data is not supported. 

# Get Market Snapshot

get_market_snapshot(code_list) 

. Description 

Get market snapshot 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>Stock list</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, stock snapshot data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Stock snapshot data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>update_time</td><td>str</td><td>Current update time.</td></tr><tr><td>last_price</td><td>float</td><td>Latest price.</td></tr><tr><td>open_price</td><td>float</td><td>Open.</td></tr><tr><td>high_price</td><td>float</td><td>High.</td></tr><tr><td>low_price</td><td>float</td><td>Low.</td></tr><tr><td>prev_close_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>suspension</td><td>bool</td><td>Is suspended or not.</td></tr><tr><td>listing_date</td><td>str</td><td>Listing date.</td></tr><tr><td>equity_valid</td><td>bool</td><td>Is stock or not.</td></tr><tr><td>issued_shares</td><td>int</td><td>Total shares.</td></tr><tr><td>total_market_val</td><td>float</td><td>Total market value.</td></tr><tr><td>net_asset</td><td>int</td><td>Net asset value.</td></tr><tr><td>net_profit</td><td>int</td><td>Net profit.</td></tr><tr><td>earning_per_share</td><td>float</td><td>Earnings per share.</td></tr><tr><td>outstanding_shares</td><td>int</td><td>Shares outstanding.</td></tr><tr><td>net_asset_per_share</td><td>float</td><td>Net assets per share.</td></tr><tr><td>circular_market_val</td><td>float</td><td>Circulation market value.</td></tr><tr><td>ey_ratio</td><td>float</td><td>Yield rate.</td></tr><tr><td>pe_ratio</td><td>float</td><td>P/E ratio.</td></tr><tr><td>pb_ratio</td><td>float</td><td>P/B ratio.</td></tr><tr><td>pe_ttm_ratio</td><td>float</td><td>P/E ratio TTM.</td></tr><tr><td>dividend_ttm</td><td>float</td><td>Dividend TTM, dividend.</td></tr><tr><td>dividend_ratio_ttm</td><td>float</td><td>Dividend rate TTM.</td></tr><tr><td>dividend_lfy</td><td>float</td><td>Dividend LFY, dividend of the previous year.</td></tr><tr><td>dividend_lfy_ratio</td><td>float</td><td>Dividend rate LFY.</td></tr><tr><td>stock-owner</td><td>str</td><td>The code of the underlying stock to which the warrant belongs or the code of the underlying stock of the option.</td></tr><tr><td>wrt_valid</td><td>bool</td><td>Is warrant or not.</td></tr><tr><td>wrt_conversion_ratio</td><td>float</td><td>Conversion ratio.</td></tr><tr><td>wrt_type</td><td>WrtType</td><td>Warrant type.</td></tr><tr><td>wrt_strike_price</td><td>float</td><td>Strike price.</td></tr><tr><td>wrt_maturity_date</td><td>str</td><td>Maturity date.</td></tr><tr><td>wrt_end_trade</td><td>str</td><td>Last trading time.</td></tr><tr><td>wrt_leverage</td><td>float</td><td>Leverage ratio.</td></tr><tr><td>wrt_ipop</td><td>float</td><td>in/out of the money.</td></tr><tr><td>wrt_break_even_point</td><td>float</td><td>Breakeven point.</td></tr><tr><td>wrt_conversion_price</td><td>float</td><td>Conversion price.</td></tr><tr><td>wrt_price_recovery_ratio</td><td>float</td><td>Price recovery ratio.</td></tr><tr><td>wrt_score</td><td>float</td><td>Comprehensive score of warrant.</td></tr><tr><td>wrt_code</td><td>str</td><td>The underlying stock of the warrant (This field has been deprecated and changed to stock-owner).</td></tr><tr><td>wrt_recovery_price</td><td>float</td><td>Warrant recovery price.</td></tr><tr><td>wrt_street_vol</td><td>float</td><td>Warrant Outstanding quantity.</td></tr><tr><td>wrt-issue_vol</td><td>float</td><td>Warrant issuance.</td></tr><tr><td>wrt_street_ratio</td><td>float</td><td>Outstanding percentage.</td></tr><tr><td>wrt delta</td><td>float</td><td>Delta value of warrant.</td></tr><tr><td>wrt_implied_volatility</td><td>float</td><td>Warrant implied volatility.</td></tr><tr><td>wrt_premium</td><td>float</td><td>Warrant premium.</td></tr><tr><td>wrt_upper_strike_price</td><td>float</td><td>Upper bound price.</td></tr><tr><td>wrt_lower_strike_price</td><td>float</td><td>lower bound price.</td></tr><tr><td>wrt_inline_price_status</td><td>PriceType</td><td>in/out of bounds</td></tr><tr><td>wrt issuer_code</td><td>str</td><td>Issuer code.</td></tr><tr><td>option_valid</td><td>bool</td><td>Is option or not.</td></tr><tr><td>option_type</td><td>OptionType</td><td>Option type.</td></tr><tr><td>strike_time</td><td>str</td><td>The option exercise date.</td></tr><tr><td>option Strike_price</td><td>float</td><td>Strike price.</td></tr><tr><td>option_contract_size</td><td>float</td><td>Number of stocks per contract.</td></tr><tr><td>option_open_interest</td><td>int</td><td>Total open contract number.</td></tr><tr><td>option_implied_volatility</td><td>float</td><td>Implied volatility.</td></tr><tr><td>option_premium</td><td>float</td><td>Premium.</td></tr><tr><td>option delta</td><td>float</td><td>Greek value Delta.</td></tr><tr><td>option_gamma</td><td>float</td><td>Greek value Gamma.</td></tr><tr><td>option_vega</td><td>float</td><td>Greek value Vega.</td></tr><tr><td>option_theta</td><td>float</td><td>Greek value Theta.</td></tr><tr><td>option_rho</td><td>float</td><td>Greek value Rho.</td></tr><tr><td>index_option_type</td><td>IndexOptionType</td><td>Index option type.</td></tr><tr><td>option_net_open_interest</td><td>int</td><td>Net open contract number.</td></tr><tr><td>option expiry_date_distance</td><td>int</td><td>The number of days from the expiry date, a negative number means it has expired.</td></tr><tr><td>option_contract_nominal_value</td><td>float</td><td>Contract nominal amount.</td></tr><tr><td>option-owner_lotmultiplier</td><td>float</td><td>Equal number of underlying stocks.</td></tr><tr><td>option_area_type</td><td>OptionAreaType</td><td>Option type (by exercise time).</td></tr><tr><td>option_contract-multiplier</td><td>float</td><td>Contract multiplier.</td></tr><tr><td>plate_valid</td><td>bool</td><td>Is plate or not.</td></tr><tr><td>plate raisecount</td><td>int</td><td>Number of stocks that raises in the plate.</td></tr><tr><td>plate_fall_count</td><td>int</td><td>Number of stocks that falls in the plate.</td></tr><tr><td>plateequal_count</td><td>int</td><td>Number of stocks that dose not change in price in the plate.</td></tr><tr><td>index_valid</td><td>bool</td><td>Is index or not.</td></tr><tr><td>index raisecount</td><td>int</td><td>Number of stocks that raises in the plate.</td></tr><tr><td>index_fall_count</td><td>int</td><td>Number of stocks that falls in the plate.</td></tr><tr><td>indexequal_count</td><td>int</td><td>Number of stocks that dose not change in the plate.</td></tr><tr><td>lot_size</td><td>int</td><td>The number of shares per lot, stock options represent the number of shares per contract and</td></tr><tr><td></td><td></td><td>futures represent contract multipliers.</td></tr><tr><td>price_spread</td><td>float</td><td>The current upward price difference.</td></tr><tr><td>ask_price</td><td>float</td><td>Ask price.</td></tr><tr><td>bid_price</td><td>float</td><td>Bid price.</td></tr><tr><td>ask_vol</td><td>float</td><td>Ask volume.</td></tr><tr><td>bid_vol</td><td>float</td><td>Bid volume.</td></tr><tr><td>enable_margin</td><td>bool</td><td>Whether financing is available (Deprecated).</td></tr><tr><td>mortgage_ratio</td><td>float</td><td>Stock mortgage rate (Deprecated).</td></tr><tr><td>long_margin_initial_ratio</td><td>float</td><td>The initial margin rate of financing (Deprecated).</td></tr><tr><td>enable_short_sell</td><td>bool</td><td>Whether short-selling is available (Deprecated).</td></tr><tr><td>short_sell_rate</td><td>float</td><td>Short-selling reference rate (Deprecated).</td></tr><tr><td>short-available_volume</td><td>int</td><td>Remaining quantity that can be sold short (Deprecated).</td></tr><tr><td>short_margin_initial_ratio</td><td>float</td><td>The initial margin rate for short selling (Deprecated).</td></tr><tr><td>sec_status</td><td>SecurityStatus</td><td>Stock status.</td></tr><tr><td>amplitude</td><td>float</td><td>Amplitude.</td></tr><tr><td>avg_price</td><td>float</td><td>Average price.</td></tr><tr><td>bid Asking_ratio</td><td>float</td><td>The Committee.</td></tr><tr><td>volume_ratio</td><td>float</td><td>Volume ratio.</td></tr><tr><td>highest52weeks_price</td><td>float</td><td>Highest price in 52 weeks.</td></tr><tr><td>lowest52weeks_price</td><td>float</td><td>Lowest price in 52 weeks.</td></tr><tr><td>highest_history_price</td><td>float</td><td>Highest historical price.</td></tr><tr><td>lowest_history_price</td><td>float</td><td>Lowest historical price.</td></tr><tr><td>pre_price</td><td>float</td><td>Pre-market price.</td></tr><tr><td>pre_high_price</td><td>float</td><td>Highest pre-market price.</td></tr><tr><td>pre_low_price</td><td>float</td><td>Lowest pre-market price.</td></tr><tr><td>pre_volume</td><td>int</td><td>Pre-market volume.</td></tr><tr><td>pre_turnover</td><td>float</td><td>Pre-market turnover.</td></tr><tr><td>pre_change_val</td><td>float</td><td>Pre-market change.</td></tr><tr><td>pre_change_rate</td><td>float</td><td>Pre-market change rate.</td></tr><tr><td>pre_amplitude</td><td>float</td><td>Pre-market amplitude.</td></tr><tr><td>after_price</td><td>float</td><td>After-hours price.</td></tr><tr><td>after_high_price</td><td>float</td><td>Highest price after-hours.</td></tr><tr><td>after_low_price</td><td>float</td><td>Lowest price after-hours.</td></tr><tr><td>after_volume</td><td>int</td><td>After-hours trading volume.</td></tr><tr><td>after_turnover</td><td>float</td><td>After-hours turnover.</td></tr><tr><td>after_change_val</td><td>float</td><td>After-hours change.</td></tr><tr><td>after_change_rate</td><td>float</td><td>After-hours change rate.</td></tr><tr><td>after_amplitude</td><td>float</td><td>After-hours amplitude.</td></tr><tr><td>overnight_price</td><td>float</td><td>Overnight price.</td></tr><tr><td>overnight_high_price</td><td>float</td><td>Overnight high.</td></tr><tr><td>overnight_low_price</td><td>float</td><td>Overnight low.</td></tr><tr><td>overnight_volume</td><td>int</td><td>Overnight volume.</td></tr><tr><td>overnight_turnover</td><td>float</td><td>Overnight turnover.</td></tr><tr><td>overnight_change_val</td><td>float</td><td>Overnight change.</td></tr><tr><td>overnight_change_rate</td><td>float</td><td>Overnight change rate.</td></tr><tr><td>overnight_amplitude</td><td>float</td><td>Overnight amplitude.</td></tr><tr><td>future_valid</td><td>bool</td><td>Is futures or not.</td></tr><tr><td>future_last_settle_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>future_position</td><td>float</td><td>Holding position.</td></tr><tr><td>future_position_change</td><td>float</td><td>Change in position.</td></tr><tr><td>future_main_contract</td><td>bool</td><td>Is future main contract or not.</td></tr><tr><td>future_last_trade_time</td><td>str</td><td>The last trading time.</td></tr><tr><td>trust_valid</td><td>bool</td><td>Is fund or not.</td></tr><tr><td>trust_dividend_yield</td><td>float</td><td>Dividend rate.</td></tr><tr><td>trust_aum</td><td>float</td><td>Asset scale.</td></tr><tr><td>trust_outstanding.units</td><td>int</td><td>Total circulation.</td></tr><tr><td>trust_netAssetValue</td><td>float</td><td>Net asset value.</td></tr><tr><td>trust_premium</td><td>float</td><td>Premium.</td></tr><tr><td>trust_assetClass</td><td>AssetClass</td><td>Asset class.</td></tr></table>


Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3   
4 ret，data $=$ quoteCtx.get_market_snapshot(['HK.00700'，'US.AAPL'])   
5 if ret $= =$ RET_OK:   
6 print(data)   
7 print(data['code'][0]) # Take the first stock code   
8 print(data['code'].values.tolist()) # Convert to list   
9 else:   
10 print('error:'，data)   
11 quoteCtx.close() # After using the connection, remember to close it to prevent 


Output


```txt
1 code name update_time last_price open_price high_price low_p 2 HK.00700 TENCENT 2025-04-07 16:09:07 435.40 441.80 462.40 3 US.AAPL APPLE 2025-04-07 05:30:43.301 188.38 193.89 199.88 4 5 wrt-issue_vol wrt_street_ratio wrt delta wrt_implied_volatility wrt/premi 6 0 NaN NaN NaN NaN NaN NaN NaN 7 1 NaN NaN NaN NaN NaN 
```

trust_outstanding_units trust_netAssetValue trust_premium trust_assetClass 

0 

NaN 

NaN 

NaN 

N/A 

NaN 

NaN 

NaN 

N/A 

HK.00700 

['HK.00700', 'US.AAPL'] 

# Interface Limitations

Request up to 60 snapshots every 30 seconds 

For each request, the maximum number of stock codes supported by the parameter code_list is 400. 

Under the authority of Hong Kong stock BMP, the maximum number of snapshots of Hong Kong securities (including warrants, CBBC, and Inline Warrants) for a single request is 20 

Under the authority of Hong Kong futures and options BMP, the maximum number of snapshots of Hong Kong futures and options for a single request is 20 

# Get Real-time Quote

get_stock_quote(code_list) 

Description 

To get real-time quotes of subscribed securities, you must subscribe first. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>Stock list. Data type of elements in the list is str.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, quotation data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

quotation data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>data_date</td><td>str</td><td>Date.</td></tr><tr><td>data_time</td><td>str</td><td>Time of latest price.</td></tr><tr><td>last_price</td><td>float</td><td>Latest price.</td></tr><tr><td>open_price</td><td>float</td><td>Open.</td></tr><tr><td>high_price</td><td>float</td><td>High.</td></tr><tr><td>low_price</td><td>float</td><td>Low.</td></tr><tr><td>prev_close_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>amplitude</td><td>int</td><td>Amplitude.</td></tr><tr><td>suspension</td><td>bool</td><td>Whether trading is suspended.</td></tr><tr><td>listing_date</td><td>str</td><td>Listing date.</td></tr><tr><td>price_spread</td><td>float</td><td>Spread.</td></tr><tr><td>dark_status</td><td>DarkStatus</td><td>Grey market transaction status.</td></tr><tr><td>sec_status</td><td>SecurityStatus</td><td>Stock status.</td></tr><tr><td>strike_price</td><td>float</td><td>Strike price.</td></tr><tr><td>contract_size</td><td>float</td><td>Contract size.</td></tr><tr><td>open_interest</td><td>int</td><td>Number of open positions.</td></tr><tr><td>implied_volatility</td><td>float</td><td>Implied volatility.</td></tr><tr><td>premium</td><td>float</td><td>Premium.</td></tr><tr><td>delta</td><td>float</td><td>Greek value Delta.</td></tr><tr><td>gamma</td><td>float</td><td>Greek value Gamma.</td></tr><tr><td>vega</td><td>float</td><td>Greek value Vega.</td></tr><tr><td>theta</td><td>float</td><td>Greek value Theta.</td></tr><tr><td>rho</td><td>float</td><td>Greek value Rho.</td></tr><tr><td>index_option_type</td><td>IndexOptionType</td><td>Index option type.</td></tr><tr><td>net_open_interest</td><td>int</td><td>Net open contract number.</td></tr><tr><td>expiration_date_distance</td><td>int</td><td>The number of days from the expiry date.</td></tr><tr><td>contract_nominal_value</td><td>float</td><td>Contract nominal amount.</td></tr><tr><td>owner LOT multiplier</td><td>float</td><td>Equal number of underlying stocks.</td></tr><tr><td>option_area_type</td><td>OptionAreaType</td><td>Option type (by exercise time).</td></tr><tr><td>contract-multiplier</td><td>float</td><td>Contract multiplier.</td></tr><tr><td>pre_price</td><td>float</td><td>Pre-market price.</td></tr><tr><td>pre_high_price</td><td>float</td><td>Pre-market high.</td></tr><tr><td>pre_low_price</td><td>float</td><td>Pre-market low.</td></tr><tr><td>pre_volume</td><td>int</td><td>Pre-market volume.</td></tr><tr><td>pre_turnover</td><td>float</td><td>Pre-market turnover.</td></tr><tr><td>pre_change_val</td><td>float</td><td>Pre-market change.</td></tr><tr><td>pre_change_rate</td><td>float</td><td>Pre-market change rate.</td></tr><tr><td>pre_amplitude</td><td>float</td><td>Pre-market amplitude.</td></tr><tr><td>after_price</td><td>float</td><td>After-hours price.</td></tr><tr><td>after_high_price</td><td>float</td><td>After-hours high.</td></tr><tr><td>after_low_price</td><td>float</td><td>After-hours low.</td></tr><tr><td>after_volume</td><td>int</td><td>After-hours volume.</td></tr><tr><td>After_turnover</td><td>float</td><td>After-hours turnover.</td></tr><tr><td>after_change_val</td><td>float</td><td>After-hours change.</td></tr><tr><td>after_change_rate</td><td>float</td><td>After-hours change rate.</td></tr><tr><td>after_amplitude</td><td>float</td><td>After-hours amplitude.</td></tr><tr><td>overnight_price</td><td>float</td><td>Overnight price.</td></tr><tr><td>overnight_high_price</td><td>float</td><td>Overnight high.</td></tr><tr><td>overnight_low_price</td><td>float</td><td>Overnight low.</td></tr><tr><td>overnight_volume</td><td>int</td><td>Overnight volume.</td></tr><tr><td>overnight_turnover</td><td>float</td><td>Overnight turnover.</td></tr><tr><td>overnight_change_val</td><td>float</td><td>Overnight change.</td></tr><tr><td>overnight_change_rate</td><td>float</td><td>Overnight change rate.</td></tr><tr><td>overnight_amplitude</td><td>float</td><td>Overnight amplitude.</td></tr><tr><td>last_settle_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>position</td><td>float</td><td>Holding position.</td></tr><tr><td>position_change</td><td>float</td><td>Daily position change.</td></tr></table>

# Example

```python
from futu import *  
quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111) 
```

```python
ret_sub, err_message = quoteCtx subscribing(['US.AAPL'], [SubType.QUOTE], subscribe # Subscribe to the K line type first. After the subscription is successful, Open if ret_sub == RET_OK: # Subscription successful ret, data = quoteCtx.get_stock-quote(['US.AAPL']) # Get real-time data of s if ret == RET_OK: print(data) print(data['code'].0]) # Take the first stock code print(data['code'].values.tolist()) # Convert to list else: print('error: ', data) else: print('subscription failed', err_message) quoteCtx.close() # Close the current connection, OpenD will automatically cancel 
```

# Output

```txt
code name data_date data_time last_price open_price high_price low_price  
0 US.AAPL APPLE 2025-04-07 05:37:21.794 188.38 193.89 199.88  
US.AAPL  
['US.AAPL'] 
```

# Tips

This API provides the function to obtain real-time data at one time. If you need to obtain pushed data continuously, please refer to the Real-time Quote Callback API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

# Get Real-time Order Book

get_order_book(code, num=10) 

Description 

To get the real-time order book of subscribed stocks, you must subscribe first. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>num</td><td>int</td><td>The requested number of price levels.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>dict</td><td>If ret == RET_OK, plate data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Order Book format as follows： 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>svr_recv_time_bid</td><td>str</td><td>The time when Futu server receives order book of bid from the exchange.</td></tr><tr><td>svr_recv_time Asking</td><td>str</td><td>The time when Futu server receives order book of ask from the exchange.</td></tr><tr><td>Bid</td><td>list</td><td>Each tuple contains the following information: Bid price, bid volume, order qty of bid, order details of bid.</td></tr><tr><td>Ask</td><td>list</td><td>Each tuple contains the following information: Ask price, ask volume, order qty of ask, order details of ask.</td></tr></table>

The format of Bid and Ask fields as follows： 

```txt
'Bid': [ (bid_price1, bid_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid1': [ (ask_price1, ask_volume1, order_num, {'orderid1': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume1, order_num, {'orderid2': order_volume1, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num, {'orderid2': order_volume2, 'orderid2': [ (ask_price1, ask_volume2, order_num 
```

# ? Example

1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3 ret_sub $=$ quoteCtx subscribing([US.AAPL], [SubType.ORDER.Book], subscribe.push $=$ 4 # First subscribe to the order type. After the subscription is successful, OpenD   
5 if ret_sub $= =$ RET_OK: # Successfully subscribed   
6 ret, data $=$ quoteCtx.get_order_book('US.AAPL', num $= 3$ # Get 3 files of real   
7 if ret $= =$ RET_OK:   
8 print(data)   
9 else:   
10 print('error:', data)   
11 else:   
12 print('subscription failed')   
13 quoteCtx.close() # Close the current connection, OpenD will automatically cancel 

# Output

```python
1 {'code': 'US.AAPL', 'name': 'APPLE', 'svr_recv_time_bid': '2025-04-07 05:39:20.3 
```

# Interface Limitations

The time field in which the Futu server receives data from the exchange. Only supports A-share Market stocks, HK stocks, ETFs, warrants, bulls and bears, and this data is only available at the opening time. 

The time field in which the Futu server receives data from the exchange. The receiving time of some data is zero, such as server restart or cached data pushed for the first time. 

# Tips

This API provides the function of obtaining real-time data at one time. If you need to obtain pushed data continuously, please refer to the Real-time OrderBook Callback API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

The real-time order book data will be returned during the current trading session for US stocks, with no need to set the session parameter. 

# Get Real-time Candlestick

get_cur_kline(code, num, ktype=SubType.K_DAY, autype=AuType.QFQ) 

. Description 

Get real-time candlestick data of subscribed stocks, you must subscribe first. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>num</td><td>int</td><td>The number of candlesticks.</td></tr><tr><td>ktype</td><td>KLTType</td><td>Candlestick type.</td></tr><tr><td>autype</td><td>AuType</td><td>Type of adjustment.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, IPO data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

IPO data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>time_key</td><td>str</td><td>Time.</td></tr><tr><td>open</td><td>float</td><td>Open.</td></tr><tr><td>close</td><td>float</td><td>Close.</td></tr><tr><td>high</td><td>float</td><td>High.</td></tr><tr><td>low</td><td>float</td><td>Low.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>pe_ratio</td><td>float</td><td>P/E ratio.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>last_close</td><td>float</td><td>Yesterday's close.</td></tr></table>


. Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3   
4 ret_sub, err_message $=$ quoteCtx subscribing([US.AAPL], [SubType.K_DAY], subscribe   
5 # First subscribe to the candlestick type. After the subscription is successful,   
6 if ret_sub $= =$ RET_OK: # Successfully subscribed   
7 ret, data $=$ quoteCtx.get.cur_kline('US.AAPL', 2, SubType.K_DAY, AuType.QFQ)   
8 if ret $= =$ RET_OK: print(data)   
9   
10 print(data['turnover_rate'][0]) # Take the first turnover rate   
11 print(data['turnover_rate'].values.tolist()) # Convert to list   
12 else:   
13 print('error:'，data)   
14 else:   
15 print('subscription failed', err_message)   
16 quoteCtx.close() # Close the current link, OpenD will automatically cancel the 

```csv
code name time_key open close high low volume tu   
0 US.AAPL APPLE 2025-04-03 00:00:00 205.54 203.19 207.49 201.25 1034190   
1 US.AAPL APPLE 2025-04-04 00:00:00 193.89 188.38 199.88 187.34 1259109   
0.00689   
[0.00689, 0.00838] 
```

# Interface Limitations

This interface is to obtain real-time candlestick, which can obtain the nearest 1000 at most. To get historical candlestick, please refer to Get historical candlestick. 

Only a stock of daily timeframe and above have P/E ratio and turnover ratio fields. 

Options related candlestick data, only supports 1 day, 1 minute, 5 minutes, 15 minutes and 60 minutes. 

# Tips

This API provides the function of obtaining candlestick data at one time. If you need to obtain pushed data continuously, please refer to the Real-time Candlestick Callback API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

# Get Real-time Time Frame Data

get_rt_data(code) 

Description 

Obtain real-time tick-by-tick data for a specified stock. (Require real-time data subscription.) 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, Time Frame data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Time Frame data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>time</td><td>str</td><td>Time.</td></tr><tr><td>is_blank</td><td>bool</td><td>Data status.</td></tr><tr><td>opened_mins</td><td>int</td><td>How many minutes have passed from 0 o'clock.</td></tr><tr><td>cur_price</td><td>float</td><td>Current price.</td></tr><tr><td>last_CLOSE</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>avg_price</td><td>float</td><td>Average price.</td></tr><tr><td>volume</td><td>float</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Transaction amount.</td></tr></table>


. Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3 ret_sub, err_message $=$ quoteCtx subscribing([US.AAPL], [SubType.RT_DATA], subsc   
4 # Subscribe to the Time Frame data type first. After the subscription is success   
5 if ret_sub $= =$ RET_OK: # Successfully subscribed   
6 ret, data $=$ quoteCtx.get_rt_data('US.AAPL') # Get Time Frame data once   
7 if ret $= =$ RET_OK:   
8 print(data)   
9 else:   
10 print('error:'，data)   
11 else:   
12 print('subscription failed', err_message)   
13 quoteCtx.close() # Close the current link, OpenD will automatically cancel the 


. Output


```txt
1 code name time is_blank opened_mins cur_price last_close a   
2 0 US.AAPL APPLE 2025-04-06 20:01:00 False 1201 183.00   
3 ... ... ... ... ... ... ... ...   
4 586 US.AAPL APPLE 2025-04-07 05:47:00 False 347 181.26   
5   
6 [587 rows x 10 columns] 
```


Tips


This API provides the function of obtaining real-time data at one time. If you need to obtain pushed data continuously, please refer to the Real-time Time Frame Callback API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

# Get Real-time Tick-by-Tick

get_rt_ticker(code, num=500) 

Description 

To get real-time tick-by-tick of subscribed stocks. (Require real-time data subscription.) 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>num</td><td>int</td><td>Number of recent tick-by-tick.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, tick-by-tick data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Tick-by-tick data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>sequence</td><td>int</td><td>Sequence number.</td></tr><tr><td>time</td><td>str</td><td>Transaction time.</td></tr><tr><td>price</td><td>float</td><td>Transaction price.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Transaction amount.</td></tr><tr><td>ticket_direction</td><td>TickerDirect</td><td>Tick-By-Tick direction.</td></tr><tr><td>type</td><td>TickerType</td><td>Tick-By-Tick type.</td></tr></table>


. Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 3   
4 ret_sub, err_message $=$ quoteCtx subscribing([US.AAPL], [SubType.TICKER], subscribe   
5 # First subscribe to each type. After the subscription is successful, OpenD will   
6 if ret_sub $= =$ RET_OK: # Subscription successful   
7 ret, data $=$ quoteCtx.get_rt-ticketer('US.AAPL', 2) # Get the last 2 transact   
8 if ret $= =$ RET_OK:   
9 print(data)   
10 print(data['turnover'][0]) # Take the first transaction amount   
11 print(data['turnover'].values.tolist()) # Convert to list   
12 else:   
13 print('error:'，data)   
14 else:   
15 print('subscription failed', err_message)   
16 quoteCtx.close() # Close the current link, OpenD will automatically cancel the e 


Output


```txt
1 code name time price volume turnover ticker_direction 2 US.AAPL APPLE 2025-04-07 05:50:23.745 181.70 2 363.40 N 3 US.AAPL APPLE 2025-04-07 05:50:24.170 181.73 1 181.73 4 363.4   
5 [363.4,181.73] 
```

# Interface Limitations

You can get up to the latest 1000 tick-by-tick data, more historical tick-by-tick data is not yet available 

Under the authority of LV1 HK futures and options market, tick-by-tick data is not available 

# Tips

This API provides the function of obtaining real-time data at one time. If you need to obtain pushed data continuously, please refer to the Real-time Tick-By-Tick Callback API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

# Get Real-time Broker Queue

# Get Real-time Broker Queue

get_broker_queue(code) 

? Description 

Obtain real-time data of market participants on the order book. (Require real-time data subscription.) 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">bid_frame_table</td><td>pd.DataFrame</td><td>If ret == RET_OK, queue of bid brokers is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr><tr><td rowspan="2">ask_frame_table</td><td>pd.DataFrame</td><td>If ret == RET_OK, queue of ask brokers is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Queue of bid brokers format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>bid_broker_id</td><td>int</td><td>Bid broker ID.</td></tr><tr><td>bid_broker_name</td><td>str</td><td>Bid broker name.</td></tr><tr><td>bid_broker_pos</td><td>int</td><td>Broker level.</td></tr><tr><td>order_id</td><td>int</td><td>Exchange order ID.</td></tr><tr><td>order_volume</td><td>int</td><td>Order volume.</td></tr></table>

Queue of ask brokers format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>ask_broker_id</td><td>int</td><td>Ask Broker ID.</td></tr><tr><td>ask_broker_name</td><td>str</td><td>Ask Broker name.</td></tr><tr><td>ask_broker_pos</td><td>int</td><td>Broker level.</td></tr><tr><td>order_id</td><td>int</td><td>Exchange order ID.</td></tr><tr><td>order_volume</td><td>int</td><td>Order volume.</td></tr></table>

Example 

from futu import * 

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111) 

ret_sub, err_message = quote_ctx.subscribe(['HK.00700'], [SubType.BROKER], subsc 

# First subscribe to the broker queue type. After the subscription is successful 

if ret_sub == RET_OK: # Subscription successful 

```python
ret, bid_frame_table, ask_frame_table = quotectx.get_broker_queue('HK.00700')  
if ret == RET_OK:  
    print(bid_frame_table)  
else:  
    print('error:", bid_frame_table)  
else:  
    print(err_message)  
quotectx.close() # Close the current connection, OpenD will automatically cancel 
```


Output


```txt
code name bid_broker_id bid_broker_n 0 HK.00700 TENCENT 5338 J.P.Morgan Broking (Hong Kong) ... ... ... ... 36 HK.00700 TENCENT 8305 Futu Securities International (Hong Kong) [37 rows x 7 columns] 
```

# Tips

This API provides the function of obtaining real-time data at one time. If you need to obtain pushed data continuously, please refer to the Real-time Broker Queue Callback API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface. 

Under the BMP & LV1 HK market quotes, the broker queue market data is not supported. 

# Get Market Status of Securities

get_market_state(code_list) 

Description 

Get market status of underlying security 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>A list of security codes that need to query for market status.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, market status data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Market status data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>market_state</td><td>MarketState</td><td>Market state.</td></tr></table>

Example 

```python
from futu import *  
quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)  
ret, data = quoteCtx.get_market_state(['SZ.000001', 'HK.00700'])  
if ret == RET_OK:  
    print(data)  
else:  
    print('error: ', data)  
quoteCtx.close() # After using the connection, remember to close it to prevent 
```

# ? Output

code 

0 SZ.000001 

stock_name 

Ping An Bank 

market_state 

AFTERNOON 

1 HK.00700 

Tencent 

AFTERNOON 

# Interface Limitations

A maximum of 10 requests per 30 seconds 

The maximum number of stock codes for each request is 400. 

# Get Capital Flow

get_capital_flow(stock_code, period_type $\cdot$ PeriodType.INTRADAY, start=None, end=None) 

Description 

Get the flow of a specific stock 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>stock_code</td><td>str</td><td>Stock code.</td></tr><tr><td>period_type</td><td>PeriodType</td><td>Period Type.</td></tr><tr><td>start</td><td>str</td><td>Start time.</td></tr><tr><td>end</td><td>str</td><td>End time.</td></tr></table>

The combination of start and end is as follows 

<table><tr><td>start type</td><td>end type</td><td>Description</td></tr><tr><td>str</td><td>str</td><td>start and end are the specified dates respectively.</td></tr><tr><td>None</td><td>str</td><td>start is 365 days before end.</td></tr><tr><td>str</td><td>None</td><td>end is 365 days after start.</td></tr><tr><td>None</td><td>None</td><td>end is the current date, start is 365 days before.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, capital flow data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Capital flow data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>in_flow</td><td>float</td><td>Net inflow of capital.</td></tr><tr><td>main_in_flow</td><td>float</td><td>Block Orders Net Inflow.</td></tr><tr><td>super_in_flow</td><td>float</td><td>Extra-large Orders Net Inflow.</td></tr><tr><td>big_in_flow</td><td>float</td><td>Large Orders Net Inflow.</td></tr><tr><td>mid_in_flow</td><td>float</td><td>Medium Orders Net Inflow.</td></tr><tr><td>sml_in_flow</td><td>float</td><td>Small Orders Net Inflow.</td></tr><tr><td>capital_flow_item_time</td><td>str</td><td>Start time string.</td></tr><tr><td>last_valid_time</td><td>str</td><td>Last valid time string of data.</td></tr></table>

# . Example

```python
from futu import *  
quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)  
ret, data = quoteCtx.get_capital_flow("HK.00700", period_type = PeriodType.INTRA  
if ret == RET_OK:  
    print(data)  
    print(data['in_flow']) # Take the first net inflow of capital  
    print(data['in_flow'].values.tolist()) # Convert to list  
else:  
    print('error:", data)  
quoteCtx.close() # After using the connection, remember to close it to prevent 
```

# Output

```txt
last_valid_time in_flow ... main_in_flow capital_flow_item_time  
0 N/A -1.857915e+08 ... -1.066828e+08 2021-06-08 00:00:00  
... ... ... ... ... ...  
245 N/A 2.179240e+09 ... 2.143345e+09 2022-06-08 00:00:00  
[246 rows x 8 columns]  
-185791500.0  
[-185791500.0, -18315000.0, -672100100.0, -714394350.0, -698391950.0, -818886750]  
... ... ... ... ...  
2031460.0, 638067040.0, 622466600.0, -351788160.0, -328529240.0, 715415020.0, 767 
```

# Interface Limitations

A maximum of 30 requests per 30 seconds 

Supported for stocks, warrants and funds only 

Historical period (day, month, year) Only provides data for the latest 1 year; Intraday period only provides data for the latest day. 

Data with historical period (day, month, year), is only supported for the last 2 years. While Data with intraday period is only supported for the latest day. 

Output data only includes tha data during Regular Trading Hours, not the data during Pre and Post-Market Hours. 

# Get Capital Distribution

get_capital_distribution(stock_code) 

Description 

Access to capital distribution 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>stock_code</td><td>str</td><td>Stock code.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, stock fund distribution data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Stock fund distribution data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>capital_insuper</td><td>float</td><td>Inflow capital quota, extra-large order.</td></tr><tr><td>capital_inbig</td><td>float</td><td>Inflow capital quota, large order.</td></tr><tr><td>capital_in_mid</td><td>float</td><td>Inflow capital quota, medium order.</td></tr><tr><td>capital_in_small</td><td>float</td><td>Inflow capital quota, small order.</td></tr><tr><td>capital_outsuper</td><td>float</td><td>Outflow capital quota, extra-large order.</td></tr><tr><td>capital_out-big</td><td>float</td><td>Outflow capital quota, large order.</td></tr><tr><td>capital_out_mid</td><td>float</td><td>Outflow capital quota, midthium order.</td></tr><tr><td>capital_out_small</td><td>float</td><td>Outflow capital quota, small order.</td></tr><tr><td>update_time</td><td>str</td><td>Updated time string.</td></tr></table>

# ? Example

1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3   
4 ret, data $=$ quoteCtx.get_capital_distribution("HK.00700")   
5 if ret $= =$ RET_OK:   
6 print(data)   
7 print(data['capital_in-big'][0]) # Take the amount of inflow capital of the   
8 print(data['capital_in-big'].values.tolist()) # Convert to list   
9 else:   
10 print('error:'，data)   
11 quoteCtx.close() # After using the connection, remember to close it to prevent 

# Output

```txt
1 capital_insuper capital_in-big ... capital_out_small update_time 2 2.261085e+09 2.141964e+09 ... 2.887413e+09 2022-06-08 15:59:59 3   
4 [1 rows x 9 columns]   
5 2141963720.0   
6 [2141963720.0] 
```

# Interface Limitations

A maximum of 30 requests per 30 seconds 

Only support stocks, warrants and funds. 

For more capital flow introduction, please refer to here . 

Output data only includes tha data during Regular Trading Hours, not the data during Pre and Post-Market Hours. 

# Get Plates of Stocks

get_owner_plate(code_list) 

Description 

Get the information of plates to which the stocks belong 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>Stock code list.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, data of the sector is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Data of the sector format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Securities code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>plate_code</td><td>str</td><td>Plate code.</td></tr><tr><td>plate_name</td><td>str</td><td>Plate name.</td></tr><tr><td>plate_type</td><td>Plate</td><td>Plate type.</td></tr></table>


. Example


1 from futu import \*   
2 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111)   
3   
4 code_list $=$ ['HK.00001']   
5 ret, data $=$ quoteCtx.get-ownerplate(code_list)   
6 if ret $= =$ RET_OK:   
7 print(data)   
8 print(data['code'][0]) # Take the first stock code   
9 print(data['plate_code'].values.tolist()) # Convert plate code to list   
10 else:   
11 print('error:'，data)   
12 quoteCtx.close() # After using the connection, remember to close it to prevent 


. Output


```txt
1 code name plate_code plate_name 2 HK.00001 CKH HOLDINGS HK.HSI Constituent ConstituentStocks in Hang Seng H 3 ... ... ... ... 4 8 HK.00001 CKH HOLDINS HK.BK1983 HK 5 [9 rows x 5 columns] 7 HK.00001 [HK.HSI Constituent', 'HK.GangGuTong', 'HK.BK1000', 'HK.BK1061', 'HK.BK1107', 'HK 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds 

The maximum number of stocks of each request list is 200 

Only supports stocks and indices 

# Get Historical Candlesticks

request_history_kline(code, start=None, end=None, ktype=KLType.K_DAY, autype=AuType.QFQ, fields ${ } = { }$ [KL_FIELD.ALL], max_count=1000, page_req_key=None, extended_time=False) 

. Description 

Get historical candlesticks 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>start</td><td>str</td><td>Start time.</td></tr><tr><td>end</td><td>str</td><td>End time.</td></tr><tr><td>ktype</td><td>KLTType</td><td>Candlestick type.</td></tr><tr><td>autype</td><td>AuType</td><td>Type of adjustment.</td></tr><tr><td>fields</td><td>KL_FIELD</td><td>List of fields to be returned.</td></tr><tr><td>max_count</td><td>int</td><td>The maximum number of candlesticks returned in this request.</td></tr><tr><td>page_req_key</td><td>bytes</td><td>The key of the page request. If the number of candlesticks between start and end is more than max_count, then None should be passed at the first time you call this interface, and the page_req_key returned by the last call must be passed in the subsequent pagerequests.</td></tr><tr><td>extended_time</td><td>bool</td><td>Need pre-market and after-hours data for US stocks or not. False: not need, True: need.</td></tr><tr><td>session</td><td>Session</td><td>Get US stocks historical k-line in session</td></tr></table>

The combination of start and end is as follows 

<table><tr><td>Start type</td><td>End type</td><td>Description</td></tr><tr><td>str</td><td>str</td><td>start and end are the specified dates respectively.</td></tr><tr><td>None</td><td>str</td><td>start is 365 days before end.</td></tr><tr><td>str</td><td>None</td><td>end is 365 days after start.</td></tr><tr><td>None</td><td>None</td><td>end is the current date, start is 365 days before.</td></tr></table>

. Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, historical candlestick data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr><tr><td>page_req_key</td><td>bytes</td><td>The key of the next page request.</td></tr></table>

Historical candlestick data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>time_key</td><td>str</td><td>Candlestick time.</td></tr><tr><td>open</td><td>float</td><td>Open.</td></tr><tr><td>close</td><td>float</td><td>Close.</td></tr><tr><td>high</td><td>float</td><td>High.</td></tr><tr><td>low</td><td>float</td><td>Low.</td></tr><tr><td>pe_ratio</td><td>float</td><td>P/E ratio.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>volume</td><td>int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>change_rate</td><td>float</td><td>Change rate.</td></tr><tr><td>last_close</td><td>float</td><td>Yesterday's close.</td></tr></table>


. Example


1 from futu import \*   
2 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111   
3 ret，data，page_req_key $=$ quoteCtx.request_history_kline('US.AAPL'，start $= 1$ 2019   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 print(data['code'][0])#Take the first stock code   
7 print(data['close'].values.tolist())#The closing price of the first page is   
8 else:   
9 print('error:'，data)   
10 while page_req_key != None:# Request all results after   
11 print('**********')   
12 ret，data，page_req_key $=$ quoteCtx.request_history_kline('US.AAPL'，start $= 1$ 2   
13 if ret $= =$ RET_OK:   
14 print(data)   
15 else:   
16 print('error:'，data) 

print('All pages are finished!') 

quote_ctx.close() # After using the connection, remember to close it to prevent 

# Output

```txt
1 code name time_key open close high low pe_   
2 US.AAPL APPLE 2019-09-11 00:00:00 52.631194 53.963447 53.992409 52.5493   
3 .. ... ... ... ... ... ... ... ...   
4 US.AAPL APPLE 2019-09-17 00:00:00 53.087346 53.265945 53.294907 52.8840   
5   
6 [5 rows x 13 columns]   
7 US.AAPL   
8 [53.9634465, 53.84156475, 52.7953125, 53.072865, 53.265945]   
9   
10 code name time_key open close high   
11 US.AAPL APPLE 2019-09-18 00:00:00 53.352831 53.76554 53.784847 52.96184   
12 All pages are finished! 
```

# Interface Restrictions

Candlestick data with timeframes of 60 minutes and below, is only supported for the last 8 years. Daily candlestick data is supported for the last 20 years. Daily above candlestick data is not restricted. 

We will issue historical candlestick quota based on your account assets and transaction conditions. Therefore, you can only obtain historical candlestick data for a limited number of stocks within 30 days. For specific rules, please refer to Subscription Quota & Historical Candlestick Quota. The historical candlestick quota you consume on that day will be automatically released after 30 days. 

A maximum of 60 requests per 30 seconds. Note: If you obtain data by page, this frequency limit rule is only applicable to the first time calling the interface, and subsequent pages request frequency is unlimited. 

Change rate, only supports timeframes of daily and above. 

Options related candlestick data, only supports 1 day, 1 minute, 5 minutes, 15 minutes and 60 minutes. 

The pre-market, after-hours and overnight candlestick of US stocks, only supports timeframes of 60 minutes and below. Since the pre-market, after-hours and overnight session of the US stock market are irregular trading hours, the candlestick data for this period may be less than 2 years. 

Turnover of US stocks, only supports data after 2015-10-12. 

# Get Adjustment Factor

get_rehab(code) 

Description 

Get the stock adjustment factor 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, data for adjustment is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Data for adjustment format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ex_div_date</td><td>str</td><td>Ex-dividend date.</td></tr><tr><td>split_base</td><td>float</td><td>Split numerator.</td></tr><tr><td>split_ert</td><td>float</td><td>Split dominator.</td></tr><tr><td>join_base</td><td>float</td><td>Joint numerator.</td></tr><tr><td>join_ert</td><td>float</td><td>Joint dominator.</td></tr><tr><td>split_ratio</td><td>float</td><td>Split ratio.</td></tr><tr><td>per_cash_div</td><td>float</td><td>Dividend per share.</td></tr><tr><td>bounce_base</td><td>float</td><td>Bounce numerator.</td></tr><tr><td>bounce_ert</td><td>float</td><td>Bounce dominator.</td></tr><tr><td>per_share_div_ratio</td><td>float</td><td>Bounce ratio.</td></tr><tr><td>transfer_base</td><td>float</td><td>Conversion numerator.</td></tr><tr><td>transfer_ert</td><td>float</td><td>Conversion dominator.</td></tr><tr><td>per_share_trans_ratio</td><td>float</td><td>Conversion ratio.</td></tr><tr><td>allot_base</td><td>float</td><td>Allotment numerator.</td></tr><tr><td>allot_ert</td><td>float</td><td>Allotment dominator.</td></tr><tr><td>allotment_ratio</td><td>float</td><td>Allotment ratio.</td></tr><tr><td>allotment_price</td><td>float</td><td>Issuance price.</td></tr><tr><td>add_base</td><td>float</td><td>Additional issuance numerator.</td></tr><tr><td>add_ert</td><td>float</td><td>Additional issuance dominator.</td></tr><tr><td>stk_spo_ratio</td><td>float</td><td>Additional issuance ratio.</td></tr><tr><td>stk_spo_price</td><td>float</td><td>Additional issuance price.</td></tr><tr><td>spin_off_base</td><td>float</td><td>Spin-off numerator.</td></tr><tr><td>spin_off_ert</td><td>float</td><td>Spin-off dominator.</td></tr><tr><td>spin_off_ratio</td><td>float</td><td>Spin-off ratio.</td></tr><tr><td>forward_adj_factorA</td><td>float</td><td>Forward adjustment factor A.</td></tr><tr><td>forward_adj_factorB</td><td>float</td><td>Forward adjustment factor B.</td></tr><tr><td>backward_adj_factorA</td><td>float</td><td>Backward adjustment factor A.</td></tr><tr><td>backward_adj_factorB</td><td>float</td><td>Backward adjustment factor B.</td></tr></table>

Price after forward adjustment $=$ price before forward adjustment * Forward adjustment factor A $^ +$ Forward adjustment factor B 

Price after backward adjustment $=$ price before backward adjustment * Backward adjustment factor A $^ +$ Backward adjustment factor B 


Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3   
4 ret, data $=$ quoteCtx.get_rehab("HK.00700")   
5 if ret $= =$ RET_OK:   
6 print(data)   
7 print(data['ex_div_date'][0]) # Take the first ex-dividend date   
8 print(data['ex_div_date'].values.tolist()) # Convert to list   
9 else:   
10 print('error:'，data)   
11 quoteCtx.close() # After using the connection, remember to close it to prevent 


. Output


```txt
1 ex_div_date split_ratio per_cash_div per_share_div_ratio per_share_trans   
2 0 2005-04-19 NaN 0.07 NaN   
3 .. ... ... ... ...   
4 15 2019-05-17 NaN 1.00 NaN   
5   
6 [16 rows x 16 columns]   
7 2005-04-19   
8 ['2005-04-19', '2006-05-15', '2007-05-09', '2008-05-06', '2009-05-06', '2010-05- 
```

Interface Limitations 

A maximum of 60 requests per 30 seconds 

# Get Option Expiration Date

get_option_expiration_date(code, index_option_type=IndexOptionType.NORMAL) 

. Description 

Query all expiration dates of option chains through the underlying stock. To obtain the complete option chain, please use it in combination with Get Option Chain. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>index_option_type</td><td>IndexOptionType</td><td>Index option type.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, option expiration date data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Option expiration date data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>strike_time</td><td>str</td><td>Exercise date.</td></tr><tr><td>option expiry_date_distance</td><td>int</td><td>The number of days from the expiry date.</td></tr><tr><td>expiration_cycle</td><td>ExpirationCycle</td><td>Expiration cycle.</td></tr></table>


. Example


1 from futu import \*   
2 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111   
3 ret, data $=$ quoteCtx.get_optionexpiration_date(code $=$ 'HK.00700')   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 print(data['strike_time'].values.tolist()) # Convert to list   
7 else:   
8 print('error:'，data)   
9 quoteCtx.close() # After using the connection, remember to close it to prevent 


. Output


```txt
1 strike_time option expiry_date_distance expiration_cycle 2 02021-04-29 4 N/A 3 12021-05-28 33 N/A 4 2021-06-29 65 N/A 5 32021-07-29 95 N/A 6 42021-09-29 157 N/A 7 52021-12-30 249 N/A 8 62022-03-30 339 N/A 9 ['2021-04-29', '2021-05-28', '2021-06-29', '2021-07-29', '2021-09-29', '2021-12-3 
```

# Interface Limitations

A maximum of 60 requests per 30 seconds 

# Get Option Chain

get_option_chain(code, index_option_type=IndexOptionType.NORMAL, start=None, end=None, option_type=OptionType.ALL, option_cond_type=OptionCondType.ALL, data_filter=None) 

# . Description

Query the option chain from an underlying stock. This interface only returns the static information of the option chain. If you need to obtain dynamic information such as quotation or trading, please use the security code returned by this interface to subscribe the required security. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Code of underlying stock.</td></tr><tr><td>index_option_type</td><td>IndexOptionType</td><td>Index option type.</td></tr><tr><td>start</td><td>str</td><td>Start date, for expiration date.</td></tr><tr><td>end</td><td>str</td><td>End date (including this day), for expiration date.</td></tr><tr><td>option_type</td><td>OptionType</td><td>Option type for call/put.</td></tr><tr><td>option_cond_type</td><td>OptionCondType</td><td>Option type for in/out of the money.</td></tr><tr><td>data_filter</td><td>OptionDataFilter</td><td>Data filter condition.</td></tr></table>

The combination of start and end is as follows: 

<table><tr><td>Start type</td><td>End type</td><td>Description</td></tr><tr><td>str</td><td>str</td><td>start and end are the specified dates respectively.</td></tr><tr><td>None</td><td>str</td><td>start is 30 days before end.</td></tr><tr><td>str</td><td>None</td><td>end is 30 days after start.</td></tr><tr><td>None</td><td>None</td><td>start is the current date, end is 30 days later.</td></tr></table>


O OptionDataFilter fields are as follows


<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>implied_volatility_min</td><td>float</td><td>Min value of implied volatility.</td></tr><tr><td>implied_volatility_max</td><td>float</td><td>Max value of implied volatility.</td></tr><tr><td>delta_min</td><td>float</td><td>Min value of Greek value Delta.</td></tr><tr><td>delta_max</td><td>float</td><td>Max value of Greek value Delta.</td></tr><tr><td>gamma_min</td><td>float</td><td>Min value of Greek value Gamma.</td></tr><tr><td>gamma_max</td><td>float</td><td>Max value of Greek value Gamma.</td></tr><tr><td>vega_min</td><td>float</td><td>Min value of Greek value Vega.</td></tr><tr><td>vega_max</td><td>float</td><td>Max value of Greek value Vega.</td></tr><tr><td>theta_min</td><td>float</td><td>Min value of Greek value Theta.</td></tr><tr><td>theta_max</td><td>float</td><td>Max value of Greek value Theta.</td></tr><tr><td>rho_min</td><td>float</td><td>Min value of Greek value Rho.</td></tr><tr><td>rho_max</td><td>float</td><td>Max value of Greek value Rho.</td></tr><tr><td>net_open_interest_min</td><td>float</td><td>Min value of net open contract number.</td></tr><tr><td>net_open_interest_max</td><td>float</td><td>Max value of net open contract number.</td></tr><tr><td>open_interest_min</td><td>float</td><td>Min value of open contract number.</td></tr><tr><td>open_interest_max</td><td>float</td><td>Max value of open contract number.</td></tr><tr><td>vol_min</td><td>float</td><td>Min value of Volume.</td></tr><tr><td>vol_max</td><td>float</td><td>Max value of Volume.</td></tr></table>

# . Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, option chain data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Option chain data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>name</td><td>str</td><td>Security name.</td></tr><tr><td>lot_size</td><td>int</td><td>Number of shares per lot, number of shares per contract for options.</td></tr><tr><td>stock_type</td><td>SecurityType</td><td>Stock type.</td></tr><tr><td>option_type</td><td>OptionType</td><td>Option type.</td></tr><tr><td>stock-owner</td><td>str</td><td>Underlying stock.</td></tr><tr><td>strike_time</td><td>str</td><td>Exercise date.</td></tr><tr><td>strike_price</td><td>float</td><td>Strike price.</td></tr><tr><td>suspension</td><td>bool</td><td>Whether is suspended.</td></tr><tr><td>stock_id</td><td>int</td><td>Stock ID.</td></tr><tr><td>index_option_type</td><td>IndexOptionType</td><td>Index option type.</td></tr><tr><td>expiration_cycle</td><td>ExpirationCycle</td><td>Expiration cycle type.</td></tr><tr><td>option_STANDARD_type</td><td>OptionStandardType</td><td>Option standard type.</td></tr><tr><td>option_settlement_mode</td><td>OptionSettlementMode</td><td>Option settlement mode.</td></tr></table>


Example


1 from futu import \*   
2 import time   
3 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111   
4 ret1, data1 $=$ quoteCtx.get_optionexpiration_date(code $=$ 'HK.00700')   
5   
6 filter1 $=$ OptionDataFilter()   
7 filter1 delta_min $= 0$ 8 filter1 delta_max $= 0.1$ 9   
10 if ret1 $= =$ RET_OK:   
11 expiration_date_list $=$ data1['strike_time'].values.tolist()   
12 for date in expiration_date_list:   
13 ret2, data2 $=$ quoteCtx.get_option_chain(code $=$ 'HK.00700'，start $\equiv$ date，end   
14 if ret2 $= =$ RET_OK:   
15 print(data2)   
16 print(data2['code'] [0]) # Take the first stock code   
17 print(data2['code'].values.tolist()) # Convert to list   
18 else:   
19 print('error:'，data2)   
20 time.sleep(3)   
21 else:   
22 print('error:'，data1)   
23 quoteCtx.close() # After using the connection, remember to close it to prevent 

. Output 

<table><tr><td>1</td><td>code</td><td>name lot_size stock_type option_type s</td></tr><tr><td>2</td><td>0 HK.TCH210429C350000</td><td>腾讯 210429 350.00 购 100 DRVT CAL</td></tr><tr><td>3</td><td>1 HK.TCH210429P350000</td><td>腾讯 210429 350.00 沽 100 DRVT PU</td></tr><tr><td>4</td><td>2 HK.TCH210429C360000</td><td>腾讯 210429 360.00 购 100 DRVT CAL</td></tr><tr><td>5</td><td>3 HK.TCH210429P360000</td><td>腾讯 210429 360.00 沽 100 DRVT PU</td></tr><tr><td>6</td><td>4 HK.TCH210429C370000</td><td>腾讯 210429 370.00 购 100 DRVT CAL</td></tr><tr><td>7</td><td>5 HK.TCH210429P370000</td><td>腾讯 210429 370.00 沽 100 DRVT PU</td></tr><tr><td>8</td><td>HK.TCH210429C350000</td><td></td></tr><tr><td>9</td><td colspan="2">[ &#x27;HK.TCH210429C350000&#x27;, &#x27;HK.TCH210429P350000&#x27;, &#x27;HK.TCH210429C360000&#x27;, &#x27;HK.TCH210429P360000&#x27; ]</td></tr><tr><td>10</td><td>...</td><td></td></tr><tr><td>11</td><td colspan="2">code name lot_size stock_type option_type stock</td></tr><tr><td>12</td><td>0 HK.TCH220330C490000</td><td>腾讯 220330 490.00 购 100 DRVT CALL</td></tr><tr><td>13</td><td>1 HK.TCH220330P490000</td><td>腾讯 220330 490.00 沽 100 DRVT PUT</td></tr><tr><td>14</td><td>2 HK.TCH220330C500000</td><td>腾讯 220330 500.00 购 100 DRVT CALL</td></tr><tr><td>15</td><td>3 HK.TCH220330P500000</td><td>腾讯 220330 500.00 沽 100 DRVT PUT</td></tr><tr><td>16</td><td>4 HK.TCH220330C510000</td><td>腾讯 220330 510.00 购 100 DRVT CALL</td></tr><tr><td>17</td><td>5 HK.TCH220330P510000</td><td>腾讯 220330 510.00 沽 100 DRVT PUT</td></tr><tr><td>18</td><td>HK.TCH220330C490000</td><td></td></tr><tr><td>19</td><td colspan="2">[ &#x27;HK.TCH220330C490000&#x27;, &#x27;HK.TCH220330P490000&#x27;, &#x27;HK.TCH220330C500000&#x27;, &#x27;HK.TCH220330P500000&#x27; ]</td></tr></table>

# Interface Limitations

A maximum of 10 requests per 30 seconds 

The upper limit of the incoming time span is 30 days 

# Tips

This interface does not support the query of expired option chains, please enter today or future date to the End date parameter. 

Open interest (OI) is updated daily and the specific timing depends on the exchange. 

For U.S. stock options, the data is updated during the PRE_MARKET session. 

For Hong Kong stock options, the data is updated after the Regular Trading Hours. 

# Get Filtered Warrant

get_warrant(stock_owner= req=None) 

Description 

Get Filtered Warrant (only warrants, CBBCs and Inline Warrants of HK market are surpported) 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>stock-owner</td><td>str</td><td>Code of the underlying stock.</td></tr><tr><td>req</td><td>WarrantRequest</td><td>Filter parameter combination.</td></tr></table>

WarrantRequest's details as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>begin</td><td>int</td><td>Data start point</td></tr><tr><td>num</td><td>int</td><td>The number of requested data.</td></tr><tr><td>sort_field</td><td>SortField</td><td>According to which field to sort.</td></tr><tr><td>ascend</td><td>bool</td><td>The sort direction.</td></tr><tr><td>type_list</td><td>list</td><td>Warrant Type Filter List.</td></tr><tr><td>issuer_list</td><td>list</td><td>Issuer filter list.</td></tr><tr><td>maturity_time_min</td><td>str</td><td>The start time of the maturity date filter range.</td></tr><tr><td>maturity_time_max</td><td>str</td><td>The end time of the maturity date filter range.</td></tr><tr><td>ipo_period</td><td>IpoPeriod</td><td>Listing period.</td></tr><tr><td>price_type</td><td>PriceType</td><td>In/out of the money.</td></tr><tr><td>status</td><td>WarrantStatus</td><td>Warrant Status.</td></tr><tr><td>cur_price_min</td><td>float</td><td>The filter lower limit (closed interval) of the latest price.</td></tr><tr><td>cur_price_max</td><td>float</td><td>The filter upper limit (closed interval) of the latest price.</td></tr><tr><td>strike_price_min</td><td>float</td><td>The lower filter limit (closed interval) of the strike price.</td></tr><tr><td>strike_price_max</td><td>float</td><td>The upper filter limit (closed interval) of the strike price.</td></tr><tr><td>street_min</td><td>float</td><td>The lower limit (closed interval) of Outstanding percentage.</td></tr><tr><td>street_max</td><td>float</td><td>The upper limit (closed interval) of Outstanding percentage.</td></tr><tr><td>conversion_min</td><td>float</td><td>The lower filter limit (closed interval) of the conversion ratio.</td></tr><tr><td>conversion_max</td><td>float</td><td>The upper filter limit (closed interval) of the conversion ratio.</td></tr><tr><td>vol_min</td><td>int</td><td>The lower filter limit (closed interval) of the volume.</td></tr><tr><td>vol_max</td><td>int</td><td>The upper filter limit (closed interval) of the volume.</td></tr><tr><td>premium_min</td><td>float</td><td>The lower filter limit (closed interval) of premium value.</td></tr><tr><td>premium_max</td><td>float</td><td>The upper filter limit (closed interval) of premium value.</td></tr><tr><td>leverage_ratio_min</td><td>float</td><td>The lower filter limit (closed interval) of the leverage ratio.</td></tr><tr><td>leverage_ratio_max</td><td>float</td><td>The upper filter limit (closed interval) of the leverage ratio.</td></tr><tr><td>delta_min</td><td>float</td><td>The lower filter limit (closed interval) of the hedge value Delta.</td></tr><tr><td>delta_max</td><td>float</td><td>The upper filter limit (closed interval) of the hedge value Delta.</td></tr><tr><td>implied_min</td><td>float</td><td>The lower filter limit (closed interval) of the implied volatility.</td></tr><tr><td>implied_max</td><td>float</td><td>The upper filter limit (closed interval) of the implied volatility.</td></tr><tr><td>recovery_price_min</td><td>float</td><td>The lower filter limit (closed interval) of the recovery price.</td></tr><tr><td>recovery_price_max</td><td>float</td><td>The upper filter limit (closed interval) of the recovery price.</td></tr><tr><td>price_recovery_ratio_min</td><td>float</td><td>The lower filter limit (closed interval) of the price recovery ratio.</td></tr><tr><td>price_recovery_ratio_max</td><td>float</td><td>The upper filter limit (closed interval) of the price recovery ratio.</td></tr></table>

# . Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, warrant data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Warrant data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>warrant_data_list</td><td>pd.DataFrame</td><td>Warrant data after filtering.</td></tr><tr><td>last_page</td><td>bool</td><td>Weather is the last page.</td></tr><tr><td>all_count</td><td>int</td><td>The total number of warrants in the filtered result.</td></tr></table>

Warrant_data_list's detail as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock</td><td>str</td><td>Warrant code.</td></tr><tr><td>stock-owner</td><td>str</td><td>Underlying stock.</td></tr><tr><td>type</td><td>WrtType</td><td>Warrant type.</td></tr><tr><td>issuer</td><td>Issuer</td><td>Issuer.</td></tr><tr><td>maturity_time</td><td>str</td><td>Maturity date.</td></tr><tr><td>list_time</td><td>str</td><td>Listing time.</td></tr><tr><td>last_trade_time</td><td>str</td><td>Last trading day.</td></tr><tr><td>recovery_price</td><td>float</td><td>Recovery price.</td></tr><tr><td>conversion_ratio</td><td>float</td><td>Conversion ratio.</td></tr><tr><td>lot_size</td><td>int</td><td>Quantity per lot.</td></tr><tr><td>strike_price</td><td>float</td><td>Strike price.</td></tr><tr><td>last_close_price</td><td>float</td><td>Yesterday's close.</td></tr><tr><td>name</td><td>str</td><td>Name.</td></tr><tr><td>cur_price</td><td>float</td><td>Current price.</td></tr><tr><td>price_change_val</td><td>float</td><td>Price change.</td></tr><tr><td>status</td><td>WarrantStatus</td><td>Warrant status.</td></tr><tr><td>bid_price</td><td>float</td><td>Bid price.</td></tr><tr><td>ask_price</td><td>float</td><td>Ask price.</td></tr><tr><td>bid_vol</td><td>int</td><td>Bid volume.</td></tr><tr><td>ask_vol</td><td>int</td><td>Ask volume.</td></tr><tr><td>volume</td><td>unsigned int</td><td>Volume.</td></tr><tr><td>turnover</td><td>float</td><td>Turnover.</td></tr><tr><td>score</td><td>float</td><td>Comprehensive score.</td></tr><tr><td>premium</td><td>float</td><td>Premium.</td></tr><tr><td>break_even_point</td><td>float</td><td>Breakeven point.</td></tr><tr><td>leverage</td><td>float</td><td>Leverage ratio.</td></tr><tr><td>ipop</td><td>float</td><td>In/out of the money.</td></tr><tr><td>price_recovery_ratio</td><td>float</td><td>Price recovery ratio.</td></tr><tr><td>conversion_price</td><td>float</td><td>Conversion price.</td></tr><tr><td>street_rate</td><td>float</td><td>Outstanding percentage.</td></tr><tr><td>street_vol</td><td>int</td><td>Outstanding quantity.</td></tr><tr><td>amplitude</td><td>float</td><td>Amplitude.</td></tr><tr><td>issue_size</td><td>int</td><td>Issue size.</td></tr><tr><td>high_price</td><td>float</td><td>High.</td></tr><tr><td>low_price</td><td>float</td><td>Low.</td></tr><tr><td>implied_volatility</td><td>float</td><td>Implied volatility.</td></tr><tr><td>delta</td><td>float</td><td>Hedging value.</td></tr><tr><td>effective_leverage</td><td>float</td><td>Effective leverage.</td></tr><tr><td>upper_strike_price</td><td>float</td><td>Upper bound price.</td></tr><tr><td>lower_strike_price</td><td>float</td><td>Lower bound price.</td></tr><tr><td>inline_price_status</td><td>PriceType</td><td>In/out of bounds.</td></tr></table>

# Example

1 from futu import \*   
2 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111)   
3   
4 req $=$ WarrantRequest()   
5 req.sort_field $=$ SortField.TURNOVER   
6 req.type_list $=$ WrtType.CALL   
7 req.cur_price_min $= 0.1$ 8 req.cur_price_max $= 0.2$ 9 ret,ls $=$ quoteCtx.get_warrant("HK.00700"，req)   
10 if ret $= =$ RET_OK:#First judge whether the interface return is normal,and then   
11 warrant_data_list, last_page, all_count $=$ ls 

```python
12 print(len(warrant_data_list), all_count, warrant_data_list)   
13 print(warrant_data_list['stock'][0]) # Take the first warrant code   
14 print(warrant_data_list['stock'].values.tolist()) # Convert to list   
15 else:   
16 print('error: ', ls)   
17   
18 req = WarrantRequest()   
19 req.sort_field = SortField.TURNOVER   
20 req.issuer_list = ['UB', 'CS', 'BI']   
21 ret, ls = quotectx.get_warrant(Market.HK, req)   
22 if ret == RET_OK:   
23 warrant_data_list, last_page, all_count = ls   
24 print(len(warrant_data_list), all_count, warrant_data_list)   
25 else:   
26 print('error: ', ls)   
27   
28 quotectx.close() # After using the connection, remember to close it to prevent 
```


? Output


```txt
1 2 2   
2 stock name stock-owner type issuer maturity_time list_time last_tr   
3 0 HK.20306 MBTENCT@EC2012A HK.00700 CALL MB 2020-12-01 2019-06-27   
4 1 HK.16545 SGTENCT@EC2102B HK.00700 CALL SG 2021-02-26 2020-07-14   
5 HK.20306   
6 ['HK.20306', 'HK.16545']   
7   
8 200 358   
9 stock name stock-owner type issuer maturity_time list_time last_t   
10 0 HK.19839 PINGANRUIYINLINGYIGOUAC HK.02318 CALL UB 2020-12-31   
11 1 HK.20084 PINGANZHONGYINLINGYIGOUAC HK.02318 CALL BI 2020-12-3   
12 . . . .   
13 198 HK.56886 UB#HSI RC2301F HK.800000 BULL UB 2023-01-30 2020-03   
14 199 HK.56895 UB#XIAMIRC2012D HK.01810 BULL UB 2020-12-30 2020-03   
15 
```

# Interface Limitations

Hong Kong stock BMP permission does not support calling this API 

A maximum of 60 requests per 30 seconds 

The maximum number of data per request is 200 

# Get Related Data of a Specific Security

get_referencestock_list(code, reference_type) 

Description 

Get related data of securities, such as: obtaining warrants related to underlying stocks, obtaining contracts related to futures 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>reference_type</td><td>SecurityReferenceType</td><td>Related data type to be obtained.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, related data of security is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Related data of security fotmat as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>lot_size</td><td>int</td><td>The number of shares per lot, contract multiplier for futures.</td></tr><tr><td>stock_type</td><td>SecurityType</td><td>Security type.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>list_time</td><td>str</td><td>Time of listing.</td></tr><tr><td>wrt_valid</td><td>bool</td><td>Whether it is a warrant.</td></tr><tr><td>wrt_type</td><td>WrtType</td><td>Warrant type.</td></tr><tr><td>wrt_code</td><td>str</td><td>The underlying stock.</td></tr><tr><td>future_valid</td><td>bool</td><td>Whether it is a future.</td></tr><tr><td>future_main_contract</td><td>bool</td><td>Whether the future main contract.</td></tr><tr><td>future_last_trade_time</td><td>str</td><td>Last trading time.</td></tr></table>


Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 3 #Get warrants related to the underlying stock   
5 ret,data $=$ quoteCtx.get.referencestock_list('HK.00700',SecurityReferenceType.u   
6 if ret $= =$ RET_OK:   
7 print(data)   
8 print(data['code'][0])#Take the first stock code   
9 print(data['code'].values.tolist())#Convert to list   
10 else:   
11 print('error:，data)   
12 print('**********')   
13 #Port related contracts   
14 ret,data $=$ quoteCtx.get.referencestock_list('HK.A50main',SecurityReferenceTypeu   
15 ifret $= =$ RET_OK:   
16 print(data)   
17 print(data['code'][0])#Take the first stock code   
18 print(data['code'].values.tolist()）#Convert to list   
19 else:   
20 print('error:，data)   
21 quoteCtx.close()#After using the connection,remember to close it to prevent 


. Output


```txt
1 code lot_size stock_type stock_name list_time wrt_valid wrt_type wrt  
2 0 HK.24719 1000 WARRANTY TENGXUNDONGYAJIUSIGUA 2018-07-20  
3 ... ... ... ... ... ... ... ... ... ... ...  
4 1617 HK.63402 10000 WARRANTY GS#TENCTRC2108Y 2020-11-26 True  
5 [1618 rows x 11 columns]  
6 HK.24719  
7  
8 ['HK.24719', 'HK.27886', 'HK.28621', 'HK.14339', 'HK.27952', 'HK.18693', 'HK.2030'  
9 ... ... ... ... ... ... ... ... ...  
10 'HK.63402']  
11 *************  
12 code lot_size stock_type stock_name list_time wrt_valid wrt_type  
13 0 HK.A50main 5000 FUTURE A50 Future Main(DEC0) False  
14 ... ... ... ... ... ... ... ... ...  
15 5 HK.A502106 5000 FUTURE A50 JUN1 False NaN  
16  
17 [6 rows x 11 columns]  
18 HK.A50main  
19 ['HK.A50main', 'HK.A502011', 'HK.A502012', 'HK.A502101', 'HK.A502103', 'HK.A502104 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds 

When obtaining warrants related to the underlying stock, it is not subject to the above frequency restriction 

# Get Futures Contract Information

get_future_info(code_list) 

. Description 

Get futures contract information 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>Futures code list. Data type of elements in the list is str.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, futures contract data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Futures contract data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Future code.</td></tr><tr><td>name</td><td>str</td><td>Future name.</td></tr><tr><td>owner</td><td>str</td><td>Subject.</td></tr><tr><td>exchange</td><td>str</td><td>Exchange.</td></tr><tr><td>type</td><td>str</td><td>Contract type.</td></tr><tr><td>size</td><td>float</td><td>Contract size.</td></tr><tr><td>size_unit</td><td>str</td><td>Contract size unit.</td></tr><tr><td>price_currency</td><td>str</td><td>Quote currency.</td></tr><tr><td>price_unit</td><td>str</td><td>Price unit.</td></tr><tr><td>min_change</td><td>float</td><td>Price change step.</td></tr><tr><td>min_change_unit</td><td>str</td><td>Unit of price change step.</td></tr><tr><td>trade_time</td><td>str</td><td>Trading time.</td></tr><tr><td>time-zone</td><td>str</td><td>Time zone.</td></tr><tr><td>last_trade_time</td><td>str</td><td>The last trading time.</td></tr><tr><td>exchange_format_url</td><td>str</td><td>Exchange format url address.</td></tr><tr><td>origin_code</td><td>str</td><td>Original future code.</td></tr></table>

# Example

```python
from futu import *  
quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)  
ret, data = quoteCtx.get_future_info(['HK.MPImain", "HK.HAImain'])  
if ret == RET_OK:  
    print(data)  
    print(data['code'].0]) # Take the first stock code  
    print(data['code'].values.tolist()) # Convert to list  
else:  
    print('error: ', data)  
quoteCtx.close() # After using the connection, remember to close it to prevent 
```

# Output

code 

name 

owner exchange 

type 

size size_unit price_currency 

0 HK.MPImain 

MPI Future Main(NOV0) 

Hang Seng Mainland 

Properties Index 

1 HK.HAImain 

HAI Future Main(NOV0) 

HK.06837 

HKEX 

Single Stock 10000.0 

HK.MPImain 

['HK.MPImain', 'HK.HAImain'] 

# Interface Limitations

A maximum of 30 requests for obtaining futures contract data interface every 30 seconds 

The maximum number of futures is 200, in the code list for each request. 

# Filter Stocks by Condition

get_stock_filter(market, filter_list, plate_code=None, begin=0, num=200) 

Description 

Filter stocks by condition 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>market</td><td>Market</td><td>Market identifier.</td></tr><tr><td>filter_list</td><td>list</td><td>The list of filter conditions.</td></tr><tr><td>plate_code</td><td>str</td><td>Plate code.</td></tr><tr><td>begin</td><td>int</td><td>Data starting point.</td></tr><tr><td>num</td><td>int</td><td>The number of requested data.</td></tr></table>

The relevant parameters of the SimpleFilter object are as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_field</td><td>StockField</td><td>Simple filter properties.</td></tr><tr><td>filter_min</td><td>float</td><td>The lower limit of the interval (closed interval).</td></tr><tr><td>filter_max</td><td>float</td><td>The upper limit of the interval (closed interval).</td></tr><tr><td>is_no_filter</td><td>bool</td><td>Whether the field does not require filtering.</td></tr><tr><td>sort</td><td>SortDir</td><td>Sort direction.</td></tr></table>

The relevant parameters of the AccumulateFilter object are as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_field</td><td>StockField</td><td>Cumulative filter properties.</td></tr><tr><td>filter_min</td><td>float</td><td>The lower limit of the interval (closed interval).</td></tr><tr><td>filter_max</td><td>float</td><td>The upper limit of the interval (closed interval).</td></tr><tr><td>is_no_filter</td><td>bool</td><td>Whether the field does not require filtering.</td></tr><tr><td>sort</td><td>SortDir</td><td>Sort direction.</td></tr><tr><td>days</td><td>int</td><td>Accumulative days of filtering data.</td></tr></table>

The relevant parameters of the FinancialFilter object are as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_field</td><td>StockField</td><td>Financial filter properties.</td></tr><tr><td>filter_min</td><td>float</td><td>The lower limit of the interval (closed interval).</td></tr><tr><td>filter_max</td><td>float</td><td>The upper limit of the interval (closed interval).</td></tr><tr><td>is_no_filter</td><td>bool</td><td>Whether the field does not require filtering.</td></tr><tr><td>sort</td><td>SortDir</td><td>Sort direction.</td></tr><tr><td>quarter</td><td>FinancialQuarter</td><td>Accumulation time of financial report.</td></tr></table>

The relevant parameters of the CustomIndicatorFilter object are as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_field1</td><td>StockField</td><td>Custom indicator filter properties.</td></tr><tr><td>stock_field1_para</td><td>list</td><td>Custom indicator parameter.</td></tr><tr><td>relative_position</td><td>RelativePosition</td><td>Relative position.</td></tr><tr><td>stock_field2</td><td>StockField</td><td>Custom indicator filter properties.</td></tr><tr><td>stock_field2_para</td><td>list</td><td>Custom indicator parameter.</td></tr><tr><td>value</td><td>float</td><td>Custom value.</td></tr><tr><td>ktype</td><td>KLTType</td><td>K line type KLTType (only supports K_60M, K_DAY, K_WEEK, K_MON four time periods).</td></tr><tr><td>consecutive_period</td><td>int</td><td>Filters data whose consecutive periods are all eligible.</td></tr><tr><td>is_no_filter</td><td>bool</td><td>Whether the field does not require filtering. True: no filtering, False: filtering. No filtering by default.</td></tr></table>

The relevant parameters of the PatternFilter object are as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_field</td><td>StockField</td><td>Pattern filter properties.</td></tr><tr><td>ktype</td><td>KLTType</td><td>K line type KLTType (only supports K_60M, K_DAY, K_WEEK, K_MON four time periods).</td></tr><tr><td>consecutive_period</td><td>int</td><td>Filters data whose consecutive periods are all eligible.</td></tr><tr><td>is_no_filter</td><td>bool</td><td>Whether the field does not require filtering. True: no filtering, False: filtering. No filtering by default.</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, stock selection data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Stock selection data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>last_page</td><td>bool</td><td>Is it the last page.</td></tr><tr><td>all_count</td><td>int</td><td>Total number of lists.</td></tr><tr><td>stock_list</td><td>list</td><td>Stock selection data.</td></tr></table>

FilterStockData's data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>stock_code</td><td>str</td><td>Stock code.</td></tr><tr><td>stock_name</td><td>str</td><td>Stock name.</td></tr><tr><td>cur_price</td><td>float</td><td>Current price.</td></tr><tr><td>cur_price_to_highest_52weeks_ratio</td><td>float</td><td>(Current price - high in 52 weeks)/high in 52 weeks.</td></tr><tr><td>cur_price_to.lowest_52weeks_ratio</td><td>float</td><td>(Current price - low in 52 weeks)/low in 52 weeks.</td></tr><tr><td>high_price_to_highest_52weeks_ratio</td><td>float</td><td>(Today's high - high in 52 weeks)/high in 52 weeks.</td></tr><tr><td>low_price_to_lowest_52weeks_ratio</td><td>float</td><td>(Today's low - low in 52 weeks)/low in 52 weeks.</td></tr><tr><td>volume_ratio</td><td>float</td><td>Volume ratio.</td></tr><tr><td>bid Asking_ratio</td><td>float</td><td>The committee.</td></tr><tr><td>lot_price</td><td>float</td><td>Price per lot.</td></tr><tr><td>market_val</td><td>float</td><td>Market value.</td></tr><tr><td>pe_annual</td><td>float</td><td>P/E ratio.</td></tr><tr><td>pe_ttm</td><td>float</td><td>P/E ratio TTM.</td></tr><tr><td>pb_rate</td><td>float</td><td>P/B ratio.</td></tr><tr><td>change_rate_5min</td><td>float</td><td>Price change in five minutes.</td></tr><tr><td>change_rate_begin_year</td><td>float</td><td>Price change of this year.</td></tr><tr><td>ps_ttm</td><td>float</td><td>P/S rate TTM.</td></tr><tr><td>pcf_ttm</td><td>float</td><td>P/CF rate TTM.</td></tr><tr><td>total_share</td><td>float</td><td>Total number of shares.</td></tr><tr><td>float_share</td><td>float</td><td>Shares outstanding.</td></tr><tr><td>float_market_val</td><td>float</td><td>Market capitalization.</td></tr><tr><td>change_rate</td><td>float</td><td>Price change rate.</td></tr><tr><td>amplitude</td><td>float</td><td>Amplitude.</td></tr><tr><td>volume</td><td>float</td><td>Average daily volume.</td></tr><tr><td>turnover</td><td>float</td><td>Average daily turnover.</td></tr><tr><td>turnover_rate</td><td>float</td><td>Turnover rate.</td></tr><tr><td>net_profit</td><td>float</td><td>Net profit.</td></tr><tr><td>net PROFIX_growth</td><td>float</td><td>Net profit growth rate.</td></tr><tr><td>sum_of.business</td><td>float</td><td>Operating income.</td></tr><tr><td>sum_of.business_growth</td><td>float</td><td>Year-on-year growth rate of operating income.</td></tr><tr><td>net_profit_rate</td><td>float</td><td>Net interest rate.</td></tr><tr><td>gross_profit_rate</td><td>float</td><td>Gross profit rate.</td></tr><tr><td>debt_asset_rate</td><td>float</td><td>Asset-liability ratio.</td></tr><tr><td>return_on_equity_rate</td><td>float</td><td>Return on net assets.</td></tr><tr><td>roic</td><td>float</td><td>Return on invested capital.</td></tr><tr><td>roa_ttm</td><td>float</td><td>Return on Assets TTM.</td></tr><tr><td>ebit_ttm</td><td>float</td><td>Earnings before interest and tax TTM.</td></tr><tr><td>ebitda</td><td>float</td><td>Earnings before interest and tax, depreciation and amortization.</td></tr><tr><td>operating_margin_ttm</td><td>float</td><td>Operating profit margin TTM.</td></tr><tr><td>ebit_margin</td><td>float</td><td>EBIT profit margin.</td></tr><tr><td>ebitda_margin</td><td>float</td><td>EBITDA profit margin.</td></tr><tr><td>financial_cost_rate</td><td>float</td><td>Financial cost rate.</td></tr><tr><td>operating_profit_ttm</td><td>float</td><td>Operating profit TTM.</td></tr><tr><td>shareholder_net_profit_ttm</td><td>float</td><td>Net profit attributable to the parent company.</td></tr><tr><td>net_profit_cash-cover_ttm</td><td>float</td><td>Proportion of cash income in profit.</td></tr><tr><td>current_ratio</td><td>float</td><td>Current ratio.</td></tr><tr><td>quick_ratio</td><td>float</td><td>Quick ratio.</td></tr><tr><td>current_asset_ratio</td><td>float</td><td>Current asset ratio.</td></tr><tr><td>current_debt_ratio</td><td>float</td><td>Current debt ratio.</td></tr><tr><td>equity-multiplier</td><td>float</td><td>Equity multiplier.</td></tr><tr><td>property_ratio</td><td>float</td><td>Property ratio.</td></tr><tr><td>cash_and_cash_equivalents</td><td>float</td><td>Cash and cash equivalents.</td></tr><tr><td>total_asset_turnover</td><td>float</td><td>Total asset turnover rate.</td></tr><tr><td>fixed_asset_turnover</td><td>float</td><td>Fixed asset turnover rate.</td></tr><tr><td>inventory_turnover</td><td>float</td><td>Inventory turnover rate.</td></tr><tr><td>operating_cash_flow_ttm</td><td>float</td><td>Operating cash flow TTM.</td></tr><tr><td>accounts_receivable</td><td>float</td><td>Net accounts receivable.</td></tr><tr><td>ebit_growth_rate</td><td>float</td><td>EBIT year-on-year growth rate.</td></tr><tr><td>operating_profit_growth_rate</td><td>float</td><td>Operating profit year-on-year growth rate.</td></tr><tr><td>total_assets_growth_rate</td><td>float</td><td>Year-on-year growth rate of total assets.</td></tr><tr><td>profit_to_shareholders_growth_rate</td><td>float</td><td>Year-on-year growth rate of net profit attributable to the parent.</td></tr><tr><td>profit_before_tax_growth_rate</td><td>float</td><td>Year-on-year growth rate of total profit.</td></tr><tr><td>eps_growth_rate</td><td>float</td><td>EPS year-on-year growth rate.</td></tr><tr><td>roe_growth_rate</td><td>float</td><td>ROE year-on-year growth rate.</td></tr><tr><td>roic_growth_rate</td><td>float</td><td>ROIC year-on-year growth rate.</td></tr><tr><td>nocf_growth_rate</td><td>float</td><td>Year-on-year growth rate of operating cash flow.</td></tr><tr><td>nocf_per_share_growth_rate</td><td>float</td><td>Year-on-year growth rate of operating cash flow per share.</td></tr><tr><td>operating_revenue_cash_cover</td><td>float</td><td>Operating cash income ratio.</td></tr><tr><td>operating_profit_to_total_profit</td><td>float</td><td>operating profit percentage.</td></tr><tr><td>basic_eps</td><td>float</td><td>Basic earnings per share.</td></tr><tr><td>diluted_eps</td><td>float</td><td>Diluted earnings per share.</td></tr><tr><td>nocf_per_share</td><td>float</td><td>Net operating cash flow per share.</td></tr><tr><td>price</td><td>float</td><td>latest price</td></tr><tr><td>ma</td><td>float</td><td>Simple moving average</td></tr><tr><td>ma5</td><td>float</td><td>5-day simple moving average</td></tr><tr><td>ma10</td><td>float</td><td>10-day simple moving average</td></tr><tr><td>ma20</td><td>float</td><td>20-day simple moving average</td></tr><tr><td>ma30</td><td>float</td><td>30-day simple moving average</td></tr><tr><td>ma60</td><td>float</td><td>60-day simple moving average</td></tr><tr><td>ma120</td><td>float</td><td>120-day simple moving average</td></tr><tr><td>ma250</td><td>float</td><td>250-day simple moving average</td></tr><tr><td>rsi</td><td>float</td><td>RSI</td></tr><tr><td>ema</td><td>float</td><td>exponential moving average</td></tr><tr><td>ema5</td><td>float</td><td>5-day exponential moving average</td></tr><tr><td>ema10</td><td>float</td><td>10-day exponential moving average</td></tr><tr><td>ema20</td><td>float</td><td>20-day exponential moving average</td></tr><tr><td>ema30</td><td>float</td><td>30-day exponential moving average</td></tr><tr><td>ema60</td><td>float</td><td>60-day exponential moving average</td></tr><tr><td>ema120</td><td>float</td><td>120日-day exponential moving average</td></tr><tr><td>ema250</td><td>float</td><td>250日-day exponential moving average</td></tr><tr><td>kdj_k</td><td>float</td><td>K value of KDJ indicator</td></tr><tr><td>kdj_d</td><td>float</td><td>D value of KDJ indicator</td></tr><tr><td>kdj_j</td><td>float</td><td>J value of KDJ indicator</td></tr><tr><td>macd_diff</td><td>float</td><td>DIFF value of MACD indicator</td></tr><tr><td>macd_dea</td><td>float</td><td>DEA value of MACD indicator</td></tr><tr><td>macd</td><td>float</td><td>MACD value of MACD indicator</td></tr><tr><td>boll_upper</td><td>float</td><td>UPPER value of BOLL indicator</td></tr><tr><td>boll middler</td><td>float</td><td>MIDDLE value of BOLL indicator</td></tr><tr><td>boll_lower</td><td>float</td><td>LOWER value of BOLL indicator</td></tr></table>


. Example


1 from futu import \*   
2 import time   
3   
4 quote_ctx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
5 simple_filter $=$ SimpleFilter()   
6 simple_filter.filter_min $= 2$ 7 simple_filter.filter_max $= 1000$ 8 simple_filter.stock_field $=$ StockField.CUR_price   
9 simple_filter.is_no_filter $=$ False 

10 # simple_filter.sort = SortDir.ASCEND   
11   
12 financial_filter $=$ FinancialFilter()   
13 financial_filter.filter_min $= 0.5$ 14 financial_filter.filter_max $= 50$ 15 financial_filter.stock_field $=$ StockField.CURRENT_RATIO   
16 financial_filter.is_no_filter $=$ False   
17 financial_filter.sort $=$ SortDir.ASCEND   
18 financial_filter.quartet $=$ FinancialQuarter.ANNUAL   
19   
20 custom_filter $=$ CustomIndicatorFilter()   
21 custom_filter.ktype $=$ KLType.K_DAY   
22 custom_filter.stock_field1 $=$ StockField.KDJ_K   
23 custom_filter.stock_field1para $=$ [10,4,4]   
24 custom_filter.stock_field2 $=$ StockField.KDJ_K   
25 custom_filter.stock_field2para $=$ [9,3,3]   
26 custom_filter(relative_position $=$ RelativePosition.MORE   
27 custom_filter.is_no_filter $=$ False   
28   
29 nBegin $= 0$ 30 last_page $=$ False   
31 ret_list $=$ list()   
32 while not last_page:   
33 nBegin $+ =$ len(ret_list)   
34 ret,ls $=$ quote_ctx.get_stock_filter(market $\equiv$ Market.HK,filter_list=[simple_f   
35 if ret $= =$ RET_OK:   
36 last_page,all_count,ret_list $= 1s$ 37 print('all count $=$ ',all_count)   
38 for item in ret_list:   
39 print(item.stock_code)#Get the stock code   
40 print(item.stock_name)#Get the stock name   
41 print(item[simple_filter])#Get the value of the variable corresp   
42 print(item[financial_filter])#Get the value of the variable corresp   
43 print(item[custom_filter])#Get the value of custom_filter   
44 else:   
45 print('error:'，ls)   
46 break   
time.sleep(3)# Sleep for 3 seconds to avoid trigger frequency limitation   
47   
48 quote_ctx.close() #After using the connection, remember to close it to prevent 

. Output 

```txt
39 39 [ stock_code:HK.08103 stock_name:hmvod Limited cur_price:2.69 current_r  
HK.08103  
hmvod Limited  
2.69  
2.69  
4.413  
...  
HK.00306  
Kwoon Chung Bus  
2.29  
2.29  
49.769 
```

# Tips

Use Get sub-plate list function to get the sub-plate code, the plates supported by conditional stock selection are respectively 

1. The industry plate and concept plate of HK market. 

2. Industry plate of US market. 

3. Shanghai and Shenzhen's industry plate, conceptual plate and geographic plate. 

Supported plate index codes 

<table><tr><td>Code</td><td>Description</td></tr><tr><td>HK.Motherboard</td><td>Main plate of HK market</td></tr><tr><td>HK.GEM</td><td>Growth Enterprise Market of HK market</td></tr><tr><td>HK.BK1911</td><td>Main plate of H-Share</td></tr><tr><td>HK.BK1912</td><td>Growth Enterprise Market of H-share</td></tr><tr><td>US.NYSE</td><td>New York Stock Exchange</td></tr><tr><td>US.AMEX</td><td>American Exchange</td></tr><tr><td>US.NASDAQ</td><td>NASDAQ</td></tr><tr><td>SH.3000000</td><td>Shanghai main plate</td></tr><tr><td>SZ.3000001</td><td>Shenzhen main plate</td></tr><tr><td>SZ.3000004</td><td>Shenzhen Growth Enterprise Market</td></tr></table>

# Interface Limitations

BMP authority of HK market does not support conditional stock filteration function 

A maximum of 10 requests per 30 seconds 

. At most 200 filter results are returned per page 

It is recommended that the filter conditions do not exceed 250, otherwise "business processing timeout did not return" may appear 

The maximum number of the same filter condition for cumulative filter properties is 10 

If you use dynamic data such as "current price" as the sorting field, the sorting of the data may change between multiple pages 

Non-similar indicators do not support comparison, and are limited to the establishment of comparison relationships between similar indicators, and comparisons across different types of indicators will cause errors. For example: MA5 and MA10 can establish a relationship. MA5 and EMA10 cannot establish a relationship. 

The same type of filter conditions of the custom indicator attribute exceeds the upper limit of 10 

Simple attributes, financial attributes, and morphological attributes do not support repeated designation of filter conditions for the same field 

Stock filter function currently does not support irregular trading hours (i.e.premarket, post-market and overnight). All results are based on regular trading hours data. 

# Get the List of Stocks in The Plate

get_plate_stock(plate_code, sort_field=SortField.CODE, ascend=True) 

Description 

Get the list of stocks in the plate, or get the constituent stocks of the stock index 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>plate_code</td><td>str</td><td>Plate code.</td></tr><tr><td>sort_field</td><td>SortField</td><td>Sort field.</td></tr><tr><td>ascend</td><td>bool</td><td>Sort direction.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, stock data of the plate is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Stock data of the plate format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>lot_size</td><td>int</td><td>The number of shares per lot, or contract multiplier for futures.</td></tr><tr><td>stock_name</td><td>str</td><td>Stock name.</td></tr><tr><td>stock_type</td><td>SecurityType</td><td>Stock type.</td></tr><tr><td>list_time</td><td>str</td><td>Time of listing.</td></tr><tr><td>stock_id</td><td>int</td><td>Stock ID.</td></tr><tr><td>main_contract</td><td>bool</td><td>Whether future main contract.</td></tr><tr><td>last_trade_time</td><td>str</td><td>Last trading time.</td></tr></table>


. Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3   
4 ret, data $=$ quoteCtx.getplate_stock('HK.BK1001')   
5 if ret $= =$ RET_OK:   
6 print(data)   
7 print(data['stock_name'][0]) # Take the first stock name   
8 print(data['stock_name'].values.tolist()) # Convert to list   
9 else:   
10 print('error:'，data)   
11 quoteCtx.close() # After using the connection, remember to close it to prevent 


. Output


```txt
1 code lot_size stock_name stock-owner stock_child_type stock_type list_t  
2 0 HK.00462 4000 Natural dairy NaN NaN ST  
3 ... ... ... ... ... ... ... ... ...  
4 9 HK.06186 1000 China Feihe Limited NaN  
5  
6 [10 rows x 10 columns]  
7 Natural Dairy  
8 ['Natural Dairy', 'China Modern Dairy', 'Yashili International', 'YuanShengTai D 
```

Interface Limitations 

A maximum of 10 requests per 30 seconds 

Commonly used sectors and index codes 

# Get Plate List

get_plate_list(market, plate_class) 

Description 

Obtain a list of stock sectors 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>market</td><td>Market</td><td>Market identification.</td></tr><tr><td>plate_class</td><td>Plate</td><td>Plate classification.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, data of the plate list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Data of the plate list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Plate code.</td></tr><tr><td>plate_name</td><td>str</td><td>Plate name.</td></tr><tr><td>plate_id</td><td>str</td><td>Plate ID.</td></tr></table>

Example 

```python
from futu import *  
quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)  
ret, data = quoteCtx.getplate_list(Market.HK, Plate.CONCEPT)  
if ret == RET_OK:  
    print(data)  
    print(data['plate_name'].0)] # Take the first plate name  
    print(data['plate_name'].values.tolist()) # Convert to list  
else:  
    print('error:", data)  
quoteCtx.close() # After using the connection, remember to close it to prevent 
```


Output


```txt
code plate_name plate_id   
0 HK.BK1000 Short Collection BK1000   
77 HK.BK1999 Funeral Concept BK1999   
[78 rows x 3 columns]   
Short Collection   
['Short Collection', 'Ali concept stocks', 'Xiongan concept stocks', 'Apple concept 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds 

# Get Stock Basic Information

get_stock_basicinfo(market, stock_type=SecurityType.STOCK, code_list=None) 

Description 

Get Stock Basic Information 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>market</td><td>Market</td><td>Market type.</td></tr><tr><td>stock_type</td><td>SecurityType</td><td>Stock type. It does not support SecurityType.DRVT.</td></tr><tr><td>code_list</td><td>list</td><td>Stock list.</td></tr></table>

Note: when both market and code_list exist, market is ignored and only code_list is effective. 

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, stock static data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Stock static data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>lot_size</td><td>int</td><td>Number of shares per lot, number of shares per contract for options ▢, contract multipliers for futures.</td></tr><tr><td>stock_type</td><td>SecurityType</td><td>Stock type.</td></tr><tr><td>stock_child_type</td><td>WrtType</td><td>Warrant type.</td></tr><tr><td>stock-owner</td><td>str</td><td>The code of the underlying stock to which the warrant belongs, or the code of the underlying stock of the option.</td></tr><tr><td>option_type</td><td>OptionType</td><td>Option type.</td></tr><tr><td>strike_time</td><td>str</td><td>The option exercise date. ▢</td></tr><tr><td>strike_price</td><td>float</td><td>Option strike price.</td></tr><tr><td>suspension</td><td>bool</td><td>Whether the option is suspended. ▢</td></tr><tr><td>listing_date</td><td>str</td><td>Listing time. ▢</td></tr><tr><td>stock_id</td><td>int</td><td>Stock ID.</td></tr><tr><td>delisting</td><td>bool</td><td>Whether is delisted or not.</td></tr><tr><td>index_option_type</td><td>str</td><td>Index option type.</td></tr><tr><td>main_contract</td><td>bool</td><td>Whether is future main contract.</td></tr><tr><td>last_trade_time</td><td>str</td><td>Last trading time. ▢</td></tr><tr><td>exchange_type</td><td>ExchType</td><td>Exchange Type.</td></tr></table>

# . Example

from futu import * 

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111) 

```python
3 ret, data = quoteCtx.get_stockbasicinfo(Market.HK,SecurityType.STOCK)   
4 if ret == RET_OK:   
5 print(data)   
6 else:   
7 print('error:',data)   
8 print('**********')   
9 ret, data = quoteCtx.get_stockbasicinfo(Market.HK,SecurityType.STOCK，['HK.069]   
10 if ret == RET_OK:   
11 print(data)   
12 print(data['name'][0]) # Take the first stock name   
13 print(data['name'].values.tolist()) # Convert to list   
14 else:   
15 print('error:',data)   
16 quoteCtx.close() # After using the connection, remember to close it to prevent 
```


Output


```sql
1 code name lot_size stock_type stock_child_type stock_OWNER 2 HK.00001 CK Hutchison 500 STOCK N/A 3 ... ... ... ... ... ... ... ... ... ... ... 4 2592 HK.09979 GREENTOWN MANAGEMENT HOLDINGS COMPANY LIMITED 1000 5 6 [2593 rows x 16 columns] ****** **** **** **** 8 code name lot_size stock_type stock_child_type stock_OWNER 9 HK.06998 JHBP 500 STOCK N/A 10 HK.00700 Tencent 100 STOCK N/A 11 JHBP 12 ['JHBP', 'Tencent'] 
```

# Tips

When input stocks are not recognized by the program (including stocks that have been delisted a long time ago and non-existent stocks), this interface still returns stock information. The "delisted" field is used to indicate that the stock does exist or not. The unified processing is: the code is displayed normally, the stock name is displayed as "unknown stock", and the other fields are default values (The integer type defaults to 0, and the string defaults to an empty string.). 

This interface is different from other market information interfaces. When other interfaces get input stocks that the program cannot recognize, they will reject the 

request and return the error description "unknown stock". 

# Get IPO Information

get_ipo_list(market) 

Description 

Get IPO information of a specific market 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>market</td><td>Market</td><td>Market identification.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, IPO data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

IPO data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>list_time</td><td>str</td><td>Listing date, expected listing date for US stocks.</td></tr><tr><td>list_timestamp</td><td>float</td><td>Listing date timestamp, expected listing date timestamp for US stocks.</td></tr><tr><td>apply_code</td><td>str</td><td>Subscription code (applicable to A-shares).</td></tr><tr><td>issue_size</td><td>int</td><td>Total number of issuance (applicable to A- shares); Total quantity of issuance (applicable to US stocks).</td></tr><tr><td>online-issue_size</td><td>int</td><td>Online issuance (applicable to A-shares).</td></tr><tr><td>apply_upper_limit</td><td>int</td><td>Subscription limit (applicable for A-shares).</td></tr><tr><td>apply_limit_market_value</td><td>int</td><td>The market value required for maximum subscription (applicable to A-shares).</td></tr><tr><td>is Estimate_ipo_price</td><td>bool</td><td>Weather to estimate the issuance price (applicable to A-shares).</td></tr><tr><td>ipo_price</td><td>float</td><td>Issuance price. (applicable to A-shares).</td></tr><tr><td>industry_pe_rate</td><td>float</td><td>Industry P/E ratio (applicable to A-shares).</td></tr><tr><td>is Estimate_winning_ratio</td><td>bool</td><td>Whether to estimate the winning rate (applicable to A-shares).</td></tr><tr><td>winning_ratio</td><td>float</td><td>Winning rate. (applicable to A-shares).</td></tr><tr><td>issue_pe_rate</td><td>float</td><td>Issue P/E ratio (applicable to A-shares).</td></tr><tr><td>apply_time</td><td>str</td><td>Subscription date string (applicable to A- shares).</td></tr><tr><td>apply_timestamp</td><td>float</td><td>Subscription date timestamp (applicable to A-shares).</td></tr><tr><td>winning_time</td><td>str</td><td>Time string of announcement date (applicable to A-shares).</td></tr><tr><td>winning_timestamp</td><td>float</td><td>Timestamp of announcement date (applicable to A-shares).</td></tr><tr><td>is_has_won</td><td>bool</td><td>Whether the winning number has been announced (applicable to A-shares).</td></tr><tr><td>winning_num_data</td><td>str</td><td>The winning number (applicable to A- shares).</td></tr><tr><td>ipo_price_min</td><td>float</td><td>Lowest offer price (applicable to HK stocks); lowest issue price (applicable to US stocks).</td></tr><tr><td>ipo_price_max</td><td>float</td><td>Highest offer price (applicable to HK stocks); highest issue price (applicable to US stocks).</td></tr><tr><td>list_price</td><td>float</td><td>List price (applicable to HK stocks).</td></tr><tr><td>lot_size</td><td>int</td><td>Number of shares per lot.</td></tr><tr><td>entrance_price</td><td>float</td><td>Entrance fee (applicable to HK stocks).</td></tr><tr><td>is subscribing_status</td><td>bool</td><td>Is it a subscription status.</td></tr><tr><td>apply_end_time</td><td>str</td><td>Subscription deadline string (applicable to HK stocks).</td></tr><tr><td>apply_end_timestamp</td><td>float</td><td>Subscription deadline timestamp.</td></tr></table>

# Example

from moomoo import \*   
quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ ret, data $=$ quoteCtx.get_ipo_list(Market.HK)   
if ret $= =$ RET_OK: print(data) print(data['code'][0]) # Take the first stock code print(data['code'].values.tolist()) # Convert to list   
else: print('error:,'data)   
quoteCtx.close() # After using the connection, remember to close it to prevent 


. Output


```txt
1 code name list_time list_timestamp apply_code issue_size online-issue  
2 0 HK.06666 Evergrande Property Services Group Limited 2020-12-02 1.606838e-  
3 1 HK.02110 Yue Kan Holdings Limited 2020-12-07 1.607270e-  
4 HK.06666  
5 ['HK.06666', 'HK.02110'] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds 

# Get global market status

get_global_state() 

. Description 

Get global status 

. Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>dict</td><td>If ret == RET_OK, global status is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Global status format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>market sz</td><td>MarketState</td><td>Shenzhen market state.</td></tr><tr><td>market_sh</td><td>MarketState</td><td>Shanghai market state.</td></tr><tr><td>market_hk</td><td>MarketState</td><td>Hong Kong market status.</td></tr><tr><td>market_hkfuture</td><td>MarketState</td><td>Hong Kong futures market status.</td></tr><tr><td>market_usfuture</td><td>MarketState</td><td>US futures market status.</td></tr><tr><td>market_us</td><td>MarketState</td><td>United States market state.</td></tr><tr><td>market_sgfuture</td><td>MarketState</td><td>Singapore futures market status.</td></tr><tr><td>market_jpfuture</td><td>MarketState</td><td>Japanese futures market status.</td></tr><tr><td>server_ver</td><td>str</td><td>OpenD version number.</td></tr><tr><td>trd_logged</td><td>bool</td><td>True: Logged into the trading server, False: Not logged into the trading server.</td></tr><tr><td>qot_logged</td><td>bool</td><td>True: Logged into the market server, False: Not logged into the market server.</td></tr><tr><td>timestamp</td><td>str</td><td>Current Greenwich timestamp.</td></tr><tr><td>local_timestamp</td><td>float</td><td>Local timestamp for OpenD.</td></tr><tr><td>program_status_type</td><td>Program statusesType</td><td>Current status.</td></tr><tr><td>program_status_desc</td><td>str</td><td>Additional description.</td></tr></table>

# Example

from futu import * 

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111) 

print(quote_ctx.get_global_state()) 

quote_ctx.close() # After using the connection, remember to close it to prevent 

# . Output

(0, {'market_sz': 'REST', 'market_us': 'AFTER_HOURS_END', 'market_sh': 'REST', 

# Get Trading Calendar

request_trading_days(market=None, start=None, end=None, code=None) 

Description 

Request trading calendar via market or code. 

Note that the trading day is obtained by excluding weekends and holidays from natural days, and the temporary market closed data is not excluded. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>market</td><td>TradeDateMarket</td><td>Market type.</td></tr><tr><td>start</td><td>str</td><td>Start date.</td></tr><tr><td>end</td><td>str</td><td>End date.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr></table>

Note: when both market and code exist, market is ignored and only code is effective. 

The combination of start and end is as follows 

<table><tr><td>Start type</td><td>End type</td><td>Description</td></tr><tr><td>str</td><td>str</td><td>start and end are the specified dates respectively.</td></tr><tr><td>None</td><td>str</td><td>start is 365 days before end.</td></tr><tr><td>str</td><td>None</td><td>end is 365 days after start.</td></tr><tr><td>None</td><td>None</td><td>start is 365 days before, end is the current date.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>list</td><td>If ret == RET_OK, data of the trading day is returned. Data type of elements in the list is dict.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Data of the trading day's format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>time</td><td>str</td><td>Time.</td></tr><tr><td>trade_date_type</td><td>TradeDateType</td><td>Trading day type.</td></tr></table>

# Example

1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 3   
4 ret, data $=$ quoteCtx.request_trading_dayi(TradeDateMarket.HK, start $= 2020 - 04 - 01$ 5 if ret $= =$ RET_OK:   
6 print(data)   
7 else:   
8 print('error:'，data)   
9 quoteCtx.close() # After using the connection, remember to close it to prevent 

# Output

```txt
1 {{time':2020-04-01'，trade_date_type':WHOLE'},{'time':2020-04-02'，} 
```

# Interface Limitations

A maximum of 30 requests per 30 seconds 

The historical trading calendar provides data for the past 10 years, and the future trading calendar is available until December 31 this year. 。 

# Get Details of Historical Candlestick Quota

get_history_kl_quota(get_detail=False) 

Description 

Get usage details of historical candlestick quota 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>get_detail</td><td>bool</td><td>Whether to return the detailed record of historical candlestick pulled.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>tuple</td><td>If ret == RET_OK, historical candlestick quota is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Historical candlestick quota format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>used_quota</td><td>int</td><td>Used quota.</td></tr><tr><td>remain_quota</td><td>int</td><td>Remaining quota.</td></tr><tr><td>detail_list</td><td>list</td><td>Detailed records of historical candlestick data pulled, including stock code and pulling time.</td></tr></table>

detail_list, the data column format is as follows 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>request_time</td><td>str</td><td>The time string of the last pull.</td></tr></table>

# Example

```python
from futu import *  
quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)  
ret, data = quoteCtx.get_history_kl_quota(get_detail=True) # Setting True means if ret == RET_OK:  
    print(data)  
else:  
    print('error:", data)  
quoteCtx.close() # After using the connection, remember to close it to prevent 
```

# Output

```txt
(2, 98, {'code': 'HK.00123', 'name': 'YUEXIU PROPERTY', 'request_time': '2023-06- 
```

# Interface Restrictions

We will issue historical candlestick quotas based on the assets and tradings of your account. Therefore, you can only obtain historical candlestick data for a limited number of stocks within 30 days. For specific rules, please refer to Subscription Quota & Historical Candlestick Quota. 

The historical candlestick quota you consume on that day will be automatically released after 30 days. 

# Set Price Reminder

set_price_reminder(code, op, key=None, reminder_type=None, reminder_freq=None, value=None, note $^ { 1 } =$ None, reminder_session_list=NONE) 

Description 

Add, delete, modify, enable, and disable price reminders for specified stocks 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code</td></tr><tr><td>op</td><td>SetPriceReminderOp</td><td>Operation type.</td></tr><tr><td>key</td><td>int</td><td>Identification, do not need to fill in the case of adding all or deleting all.</td></tr><tr><td>reminder_type</td><td>PriceReminderType</td><td>The type of price reminder, this input parameter will be ignored when delete, enable, or disable.</td></tr><tr><td>reminder_freq</td><td>PriceReminderFreq</td><td>The frequency of price reminder, this input parameter will be ignored when delete, enabled, or disable.</td></tr><tr><td>value</td><td>float</td><td>Reminder value, the input parameter will be ignored when delete, enable, or disable.</td></tr><tr><td>note</td><td>str</td><td>The note set by the user, note supports no more than 20 Chinese characters, the input parameter will</td></tr><tr><td></td><td></td><td>be ignored when delete, enable, or disable.</td></tr><tr><td>reminder_session_list</td><td>list</td><td>The session for US stocks price reminder, this input parameter will be ignored when delete, enable, or disable.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">key</td><td>int</td><td>If ret == RET_OK, The price reminder key of the operation is returned. When deleting all reminders of a specific stock, 0 is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

. Example 

1 from futu import \*   
2 import time   
3 class PriceReminderTest(PriceReminderHandlerBase):   
4 def on_recv_rsp(self, rsp_pb):   
5 ret_code, content $=$ super(PriceReminderTest,self).on_recv_rsp(rsp_pb)   
6 if ret_code != RET_OK:   
7 print("PriceReminderTest: error, msg: %s" % content)   
8 return RET_ERROR, content   
9 print("PriceReminderTest", content)   
10 return RET_OK, content   
11 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
12 handler $=$ PriceReminderTest()   
13 quoteCtx.sethandler(handle)   
14 ret,data $=$ quoteCtx.get_market_snapshot(['US.AAPL'])   
15 if ret $= =$ RET_OK:   
16 bid_price $=$ data['bid_price'][0] # Get real-time bid price   
17 ask_price $=$ data['ask_price'][0] # Get real-time selling price 

```python
18 # Set a reminder for AAPL(24H) when the selling price is lower than (ask_price)  
19 ret Asking, ask_data = quoteCtx.set_price_reminder(code='US.AAPL', op=SetPrice  
20 if ret Asking == RET_OK:  
21 print('When the selling price is lower than (ask_price-1), remind that this is the price')  
22 else:  
23 print('error:", ask_data)  
24 # Set a reminder for AAPL(24H) when the bid price is higher than (bid_price+1)  
25 ret_bid, bid_data = quoteCtx.set_price_reminder(code='US.AAPL', op=SetPrice  
26 if ret_bid == RET_OK:  
27 print('When the bid price is higher than (bid_price+1), the reminder is set')  
28 else:  
29 print('error:", bid_data)  
30 time.sleep(15)  
31 quoteCtx.close() 
```

# Output

1 

When the selling price is lower than (ask_price-1), the reminder is set successfu When the bid price is higher than (bid_price+1), the reminder is set successfull 

# Tips

Trading volume in API is based on shares. A-shares are shown in lots in Futubull Client. 

The type of price alert has minimum precision, as follows: 

TURNOVER_UP: The minimum precision of the turnover is 10 (Yuan, Hong Kong dollar, US dollar). The value passed in will be automatically rounded down to an integer multiple of the minimum precision. If you set 00700 transaction volume 102 yuan reminder, you will get 00700 transaction volume 100 yuan reminder. After setting; if you set 00700 transaction volume 8 yuan reminder, you will get 00700 transaction volume 0 yuan reminder after setting. 

VOLUME_UP: The minimum accuracy of A-share trading volume is 1000 shares, and the minimum accuracy of other market stock trading volume is 10 shares. The value passed in will be automatically rounded down to an integer multiple of the minimum precision. 

BID_VOL_UP, ASK_VOL_UP: The minimum precision for buying and selling of Ashares is 100 shares. The value passed in will be automatically rounded down to an integer multiple of the minimum precision. 

The precision of the remaining price alert types supports up to 3 decimal places 

# Interface Limitations

A maximum of 60 requests per 30 seconds 

The upper limit of reminders that can be set for each type of each stock is 10 

# Get Price Reminder List

get_price_reminder(code=None, market=None) 

Description 

Get a list of price reminders set for the specified stock or market 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Specified stock code.</td></tr><tr><td>market</td><td>Market</td><td>Specified market type.</td></tr></table>

Note: Choose either code or market, and code takes precedence if both exist. 

. Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, price reminder data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Price reminder data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>key</td><td>int</td><td>Identification, used to modify the price reminder.</td></tr><tr><td>reminder_type</td><td>PriceReminderType</td><td>The type of price reminder.</td></tr><tr><td>reminder_freq</td><td>PriceReminderFreq</td><td>The frequency of price reminder.</td></tr><tr><td>value</td><td>float</td><td>Remind value.</td></tr><tr><td>enable</td><td>bool</td><td>Whether to enable.</td></tr><tr><td>note</td><td>str</td><td>Note.</td></tr><tr><td>reminder_session_list</td><td>list</td><td>Price reminder session list for US stocks</td></tr></table>

# Example

1 from futu import \*   
2 quoteCtx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111)   
3   
4 ret，data $=$ quoteCtx.get_price Reminder(code $=$ 'US.AAPL')   
5 if ret $= =$ RET_OK:   
6 print(data)   
7 print(data['key'].values.tolist()) # Convert to list   
8 else:   
9 print('error:'，data)   
10 print('***********)   
11 ret，data $=$ quoteCtx.get_price reminder(code $=$ None，market $=$ Market.US)   
12 if ret $= =$ RET_OK:   
13 print(data)   
14 if data.shape[0] $>0$ ：#If the price remind list is not empty   
15 print(data['code'] [0]) # Take the first stock code   
16 print(data['code'].values.tolist()) # Convert to list   
17 else:   
18 print('error:'，data)   
19 quoteCtx.close() # After using the connection, remember to close it to prevent 

# Output

```txt
1 code name key reminder_type reminder_freq value enable note 2 US.AAPL APPLE 1744021708234288125 BID.Price_UP ALWAYS 184.37 
```

```txt
3 1 US.AAPL APPLE 1744022257052794489 BID.Price_UP ALWAYS 185.50   
4 2 US.AAPL APPLE 1744021708211891867 ASK.Price_DOWN ALWAYS 182.54   
5 3 US.AAPL APPLE 1744022257023211123 ASK.Price_DOWN ALWAYS 183.70   
6 [1744021708234288125, 1744022257052794489, 1744021708211891867, 17440222570232111   
7   
8 code name key reminder_type reminder_freq value enable   
9 0 US.AAPL APPLE 1744021708234288125 BID.Price_UP ALWAYS 184.37   
10 1 US.AAPL APPLE 1744022257052794489 BID.Price_UP ALWAYS 185.50   
11 2 US.AAPL APPLE 1744021708211891867 ASK.Price_DOWN ALWAYS 182.54   
12 3 US.AAPL APPLE 1744022257023211123 ASK.Price_DOWN ALWAYS 183.70   
13 4 US.NVDA NVIDIA 1739697581665326308 PRICE_DOWN ALWAYS 102.00   
14 US.AAPL   
15 ['US.AAPL', 'US.AAPL', 'US.AAPL', 'US.AAPL', 'US.NVDA'] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds 

# Get The Watchlist

get_user_security(group_name) 

. Description 

Get a list of a specified group from watchlist 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>group_name</td><td>str</td><td>The name of the specified group from watchlist.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, watchlist is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Watchlist data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>lot_size</td><td>int</td><td>Number of shares per lot, number of shares per contract for options, contract multiplier for futures.</td></tr><tr><td>stock_type</td><td>SecurityType</td><td>Stock type.</td></tr><tr><td>stock_child_type</td><td>WrtType</td><td>Warrant type.</td></tr><tr><td>stock-owner</td><td>str</td><td>The code of the underlying stock to which the warrant belongs, or the code of the underlying stock of the option.</td></tr><tr><td>option_type</td><td>OptionType</td><td>Option type.</td></tr><tr><td>strike_time</td><td>str</td><td>The option exercise date.</td></tr><tr><td>strike_price</td><td>float</td><td>Option strike price.</td></tr><tr><td>suspension</td><td>bool</td><td>Whether the option is suspended.</td></tr><tr><td>listing_date</td><td>str</td><td>Listing date.</td></tr><tr><td>stock_id</td><td>int</td><td>Stock ID.</td></tr><tr><td>delisting</td><td>bool</td><td>Whether is delisted.</td></tr><tr><td>main_contract</td><td>bool</td><td>Whether is future main contract.</td></tr><tr><td>last_trade_time</td><td>str</td><td>Last trading time.</td></tr></table>


Example


1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 3   
4 ret, data $=$ quoteCtx.get_user_security("A")   
5 if ret $= =$ RET_OK:   
6 print(data)   
7 if data.shape[0] $>0$ # If the user security list is not empty   
8 print(data['code'] [0]) # Take the first stock code   
9 print(data['code'].values.tolist()) # Convert to list   
10 else:   
11 print('error:'，data)   
12 quoteCtx.close() # After using the connection, remember to close it to prevent 

```txt
code name lot_size stock_type stock_child_type stock-owner option_type st 0 HK.HSImain HSI Future Main(NOV0) 50 FUTURE N/A 1 HK.00700 Tencent Holdings 100 STOCK N/A HK.HSImain ['HK.HSImain', 'HK.00700'] 
```

# Tips

The corresponding Chinese and English names of the system group are as follows 

<table><tr><td>Chinese</td><td>English</td></tr><tr><td>全部</td><td>All</td></tr><tr><td>沪深</td><td>CN</td></tr><tr><td>港股</td><td>HK</td></tr><tr><td>美股</td><td>US</td></tr><tr><td>期权</td><td>Options</td></tr><tr><td>港股期权</td><td>HK options</td></tr><tr><td>美股期权</td><td>US options</td></tr><tr><td>特别关注</td><td>Starred</td></tr><tr><td>期货</td><td>Futures</td></tr></table>

# Interface Limitations

A maximum of 10 requests per 30 seconds 

Does not support position (Positions), fund treasure (Mutual Fund), foreign exchange (Forex) group query 

# Get Groups From Watchlist

get_user_security_group(group_type $\cdot$ UserSecurityGroupType.ALL) 

. Description 

Get a list of groups from the user watchlist 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>group_type</td><td>UserSecuritygroupId</td><td>Group type.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, group data of watchlist is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Group data of watchlist format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>group_name</td><td>str</td><td>Group name.</td></tr><tr><td>group_type</td><td>SecurityGroupType</td><td>Group type.</td></tr></table>

Example 

1 from futu import \* quoteCtx $=$ OpenQuoteContext(host $= 127.0.0.1$ ,port $= 11111$ 2   
3   
4 ret, data $=$ quoteCtx.get_user_security_group(group_type $=$ UserSecuritygroupIdType 

```python
5 if ret == RET_OK:  
6 print(data)  
7 else:  
8 print('error: ', data)  
9 quoteCtx.close() # After using the connection, remember to close it to prevent 
```


Output


```txt
1 group_name group_type   
2 0 Options SYSTEM   
3 .. ... C CUSTOM   
4 12 C   
5   
6 [13 rows x 2 columns] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds 

# Modify the Watchlist

modify_user_security(group_name, op, code_list) 

Description 

Modify the specific group from the watchlist (you cannot modify the system group) 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>group_name</td><td>str</td><td>The name of the group from the watchlist that needs to be modified.</td></tr><tr><td>op</td><td>ModifyUserSecurityOp</td><td>Operation type.</td></tr><tr><td>code_list</td><td>list</td><td>Stock list.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">msg</td><td rowspan="2">str</td><td>If ret == RET_OK, &quot;success&quot; is returned.</td></tr><tr><td>If ret != RET_OK, error description is returned.</td></tr></table>

. Example 

```python
1 from futu import *
2 quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)
3
4 ret, data = quoteCtxmodify_user_security("A", ModifyUserSecurityOp添, ['HK.00])
5 if ret == RET_OK:
6 print(data) # Return success
7 else:
```

8 

print('error: data) quote_ctx.close() # After using the connection, remember to close it to prevent 

# . Output

1 

success 

# Interface Limitations

A maximum of 10 requests per 30 seconds 

You can only modify custom groups, not the system group 

There is an upper limit on the number of "all" watchlist: 500 for untraded customers and 2000 for traded clients (when adding stocks to other groups, the "all" watchlist will also increase synchronously) 

If there are multiple groups with a same name, the first group will be operated 

# Price Reminder Callback

on_recv_rsp(self, rsp_pb) 

# Description

The price reminder notification callback, asynchronously handles the notification push that has been set to the price reminder. After receiving the real-time price notification, it will call back to this function. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Qot_UpdatePriceReminder_pb2.Response</td><td>This parameter does not need to be processed directly in the derived class.</td></tr></table>

# ? Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>dict</td><td>If ret == RET_OK, price reminder is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Price reminder format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code.</td></tr><tr><td>name</td><td>str</td><td>Stock name.</td></tr><tr><td>price</td><td>float</td><td>Current price.</td></tr><tr><td>change_rate</td><td>str</td><td>Current change rate.</td></tr><tr><td>market_status</td><td>PriceReminderMarketStatus</td><td>The time period for triggering.</td></tr><tr><td>content</td><td>str</td><td>Text content of price reminder.</td></tr><tr><td>note</td><td>str</td><td>Note.</td></tr><tr><td>key</td><td>int</td><td>Price reminder identification.</td></tr><tr><td>reminder_type</td><td>PriceReminderType</td><td>The type of price reminder.</td></tr><tr><td>set_value</td><td>float</td><td>The reminder value set by the user.</td></tr><tr><td>cur_value</td><td>float</td><td>The value when the reminder was triggered.</td></tr></table>


. Example


1 import time   
2 from futu import \*   
3   
4 class PriceReminderTest(PriceReminderHandlerBase):   
5 def on_recv_rsp(self, rsp_pb):   
6 ret_code，content $=$ super(PriceReminderTest,self).on_recv_rsp(rsp_pb)   
7 if ret_code != RET_OK:   
8 print("PriceReminderTest: error，msg:%s"% content)   
9 return RET_ERROR, content   
10 print("PriceReminderTest"，content）# PriceReminderTest's own processing   
11 return RET_OK, content   
12 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
13 handler $=$ PriceReminderTest()   
14 quoteCtx.sethandler(handle)# Set price reminder notification callback   
15 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
16 quoteCtx.close() # Close the current connection, OpenD will automatically cancel 

1 

PriceReminderTest {'code': 'US.AAPL', 'name': 'APPLE', 'price': 185.750, 'change 

# Tips

This interface provides the function of continuously obtaining pushed data. If you need to obtain real-time data at one time, please refer to the Get Price Reminder List API. 

For the difference between get real-time data and real-time data callback, please refer to How to Get Real-time Quotes Through Subscription Interface API. 

# Quotation Definitions

# Cumulative Filter Properties

StockField 

. NONE 

unknown 

? CHANGE_RATE 

Yield 

. AMPLITUDE 

Amplitude 

. VOLUME 

Average daily trading volume 

TURNOVER 

Average daily turnover 

. TURNOVER_RATE 

Turnover rate 

# Asset Types

AssetClass 

UNKNOW 

Unknown 

. STOCK 

Stocks 

. BOND 

Bonds 

. COMMODITY 

Commodities 

CURRENCY_MARKET 

Currency markets 

FUTURE 

Futures 

. SWAP 

Swaps 

# Corporate Action

# Dark Disk Status

DarkStatus 

. NONE 

No grey market trading 

. TRADING 

Ongoing grey market trading 

END 

Grey market trading finished 

# Financial Filter Properties

StockField 

NONE 

unknown 

. NET_PROFIT 

Net profit 

. NET_PROFIX_GROWTH 

Net profit growth rate 

. SUM_OF_BUSINESS 

Operating income 

SUM_OF_BUSINESS_GROWTH 

Year-on-year growth rate of operating income 

NET_PROFIT_RATE 

Net profit rate 

. GROSS_PROFIT_RATE 

Gross profit margin 

. DEBT_ASSET_RATE 

Asset-liability ratio 

. RETURN_ON_EQUITY_RATE 

Return on equity 

ROIC 

Return on invested capital 

ROA_TTM 

Return on assets TTM 

. EBIT_TTM 

Earnings before interest and tax TTM 

EBITDA 

Earnings before interest, tax, depreciation and amortization 

. OPERATING_MARGIN_TTM 

Operating profit margin TTM 

. EBIT_MARGIN 

EBIT margin 

. EBITDA_MARGIN 

EBITDA margin 

. FINANCIAL_COST_RATE 

Financial cost rate 

. OPERATING_PROFIT_TTM 

Operating profit TTM 

. SHAREHOLDER_NET_PROFIT_TTM 

Net profit attributable to the parent company 

NET_PROFIT_CASH_COVER_TTM 

The proportion of cash income in profit 

CURRENT_RATIO 

Current ratio 

. QUICK_RATIO 

Quick ratio 

CURRENT_ASSET_RATIO 

Liquidity rate 

. CURRENT_DEBT_RATIO 

Current debt ratio 

. EQUITY_MULTIPLIER 

Equity multiplier 

. PROPERTY_RATIO 

Equity ratio 

. CASH_AND_CASH_EQUIVALENTS 

Cash and cash equivalent 

TOTAL_ASSET_TURNOVER 

Total asset turnover rate 

. FIXED_ASSET_TURNOVER 

Fixed asset turnover rate 

. INVENTORY_TURNOVER 

Inventory turnover rate 

OPERATING_CASH_FLOW_TTM 

Operating cash flow TTM 

. ACCOUNTS_RECEIVABLE 

Net accounts receivable 

EBIT_GROWTH_RATE 

Year-on-year growth rate of EBIT 

OPERATING_PROFIT_GROWTH_RATE 

Year-on-year growth rate of operating profit 

TOTAL_ASSETS_GROWTH_RATE 

Year-on-year growth rate of total assets 

PROFIT_TO_SHAREHOLDERS_GROWTH_RATE 

Year-on-year growth rate of net profit attributed to parent company owner 

PROFIT_BEFORE_TAX_GROWTH_RATE 

Year-on-year growth rate of total profit 

. EPS_GROWTH_RATE 

Year-on-year growth rate of EPS 

. ROE_GROWTH_RATE 

Year-on-year growth rate of ROE 

ROIC_GROWTH_RATE 

Year-on-year growth rate of ROIC 

NOCF_GROWTH_RATE 

Year-on-year growth rate of operating cash flow 

? NOCF_PER_SHARE_GROWTH_RATE 

Year-on-year growth rate of operating cash flow per share 

OPERATING_REVENUE_CASH_COVER 

Operating cash cover ratio 

. OPERATING_PROFIT_TO_TOTAL_PROFIT 

Operating profit ratio 

. BASIC_EPS 

Basic earnings per share 

. DILUTED_EPS 

Diluted earnings per share 

. NOCF_PER_SHARE 

Net operating cash flow per share 

# Financial Filter Properties Period

FinancialQuarter 

. NONE 

unknown 

ANNUAL 

annual report 

. FIRST_QUARTER 

First quarter report 

INTERIM 

Interim report 

. THIRD_QUARTER 

Third quarter report 

. MOST_RECENT_QUARTER 

Latest quarter report 

# Custom indicator attributes

# StockField

. NONE 

Unknown 

. PRICE 

latest price 

. MA5 

Simple moving average 

. MA5 

5-day simple moving average (Not recommended) 

. MA10 

10-day simple moving average (Not recommended) 

MA20 

20-day simple moving average (Not recommended) 

. MA30 

30-day simple moving average (Not recommended) 

. MA60 

60-day simple moving average (Not recommended) 

. MA120 

120-day simple moving average (Not recommended) 

. MA250 

250-day simple moving average (Not recommended) 

. RSI 

# RSI

. EMA 

Exponential moving average 

. EMA5 

5-day exponential moving average (Not recommended) 

. EMA10 

10-day exponential moving average (Not recommended) 

. EMA20 

20-day exponential moving average (Not recommended) 

EMA30 

30-day exponential moving average (Not recommended) 

. EMA60 

60-day exponential moving average (Not recommended) 

EMA120 

120-day exponential moving average (Not recommended) 

EMA250 

250-day exponential moving average (Not recommended) 

KDJ_K 

K value of KDJ indicator 

KDJ_D 

D value of KDJ indicator 

. KDJ_J 

J value of KDJ indicator 

. MACD_DIFF 

DIFF value of MACD indicator 

MACD_DEA 

DEA value of MACD indicator 

. MACD 

MACD value of MACD indicator 

BOLL_UPPER 

UPPER value of BOLL indicator 

. BOLL_MIDDLER 

MIDDLER value of BOLL indicator 

? BOLL_LOWER 

LOWER value of BOLL indicator 

VALUE 

Custom value (stock_field1 does not support this field) 

# Relative position

RelativePosition 

NONE 

Unknown 

MORE 

Stock_field1 is greater than stock_field2 

LESS 

Stock_field1 is less than stock_field2 

CROSS_UP 

Stock_field1 cross over stock_field2 

CROSS_DOWN 

Stock_field1 cross below stock_field2 

# Pattern attributes

PatternField 

. NONE 

未知

. MA_ALIGNMENT_LONG 

MA bullish alignment $( \mathsf { M A S } > \mathsf { M A } 1 0 > \mathsf { M A } 2 0 > \mathsf { M A } 3 0 > \mathsf { M A } 6 0$ for two consecutive days, and the closing price of the day is greater than the closing price of the previous day) 

. MA_ALIGNMENT_SHORT 

MA bearish alignment $( \mathsf { M A S } < \mathsf { M A } 1 0 < \mathsf { M A } 2 0 < \mathsf { M A } 3 0 < \mathsf { M A } 6 0$ for two consecutive days, and the closing price of the day is less than the closing price of the previous day) 

EMA_ALIGNMENT_LONG 

EMA bullish alignment $( \mathsf { E M A S } > \mathsf { E M A 1 0 } > \mathsf { E M A 2 0 } > \mathsf { E M A 3 0 } > \mathsf { E M A 6 0 }$ for two consecutive days, and the closing price of the day is greater than the closing price of the previous day) 

EMA_ALIGNMENT_SHORT 

EMA bearish alignment $( \mathsf { E M A 5 } < \mathsf { E M A 1 0 } < \mathsf { E M A 2 0 } < \mathsf { E M A 3 0 } < \mathsf { M A 6 0 }$ for two consecutive days, and the closing price of the day is less than the closing price of the previous day) 

? RSI_GOLD_CROSS_LOW 

RSI low golden cross (short-term RSI crosses over long-term RSI below 50 (short-term RSI of the previous day is less than long-term RSI, short-term RSI of the current day is greater than long-term RSI)) 

. RSI_DEATH_CROSS_HIGH 

RSI high dead cross (short-term RSI crosses below long-term RSI above 50 (short-term RSI of the previous day is greater than long-term RSI, short-term RSI of the current day is less than long-term RSI)) 

. RSI_TOP_DIVERGENCE 

RSI top divergence (two adjacent candlestick peaks, the CLOSE of the later peak $>$ the CLOSE of the earlier peak, the RSI12 value of the later peak $<$ the RSI12 value of the earlier peak) 

. RSI_BOTTOM_DIVERGENCE 

RSI bottom divergence (two adjacent candlestick troughs, the CLOSE of the later trough $<$ the CLOSE of the earlier trough, the RSI12 value of the later trough $>$ the RSI12 value of the earlier trough) 

. KDJ_GOLD_CROSS_LOW 

KDJ low golden cross (D value is less than or equal to 30, and the K value of the previous day is less than the D value, and the K value of the day is greater than the D value) 

KDJ_DEATH_CROSS_HIGH 

KDJ high death cross (D value is greater than or equal to 70, and the K value of the previous day is greater than the D value, and the K value of the day is less than the D value) 

. KDJ_TOP_DIVERGENCE 

KDJ top divergence (two adjacent candlestick peaks, the CLOSE of the later peak $>$ the CLOSE of the earlier peak, the J value of the later peak $<$ the J value of the earlier peak) 

KDJ_BOTTOM_DIVERGENCE 

KDJ bottom divergence (two adjacent candlestick troughs, the CLOSE of the later trough < the CLOSE of the earlier trough, the J value of the later trough $>$ the J value of the earlier trough) 

. MACD_GOLD_CROSS_LOW 

MACD golden cross (DIFF crosses over DEA (DIFF is less than DEA of the previous day, and DIFF is greater than DEA of the current day)) 

MACD_DEATH_CROSS_HIGH 

MACD dead cross (DIFF crosses below DEA (DIFF is greater than DEA of the previous day, and DIFF is less than DEA of the current day)) 

. MACD_TOP_DIVERGENCE 

MACD top divergence (two adjacent candlestick peaks, the CLOSE of the later peak $>$ the CLOSE of the earlier peak, the MACD value of the later peak $<$ the MACD value of the earlier peak) 

. MACD_BOTTOM_DIVERGENCE 

MACD bottom deviation (two adjacent candlestick troughs, the CLOSE of the later trough < the CLOSE of the earlier trough, the MACD value of the later trough $>$ the MACD value of the earlier trough) 

. BOLL_BREAK_UPPER 

Break up bollinger upper bound (the stock price of the previous day was lower than the upper bound, and the stock price of the current day is greater than the upper bound) 

. BOLL_BREAK_LOWER 

Break up bollinger lower bound (the stock price of the previous day was greater than the lower bound, and the stock price of the current day is less than the lower bound) 

. BOLL_CROSS_MIDDLE_UP 

Cross over bollinger mid line (the stock price of the previous day was lower than the mid line, and the stock price of the current day is greater than the mid line) 

. BOLL_CROSS_MIDDLE_DOWN 

Cross below bollinger mid line (the stock price of the previous day was greater than the mid line, and the stock price of the current day is less than the mid line) 

# Watchlist Group Type

UserSecurityGroupType 

. NONE 

unknown 

. CUSTOM 

Custom groups 

SYSTEM 

System groups 

. ALL 

All groups 

# Index Option Category

IndexOptionType 

. NONE 

unknown 

NORMAL 

Ordinary index option 

. SMALL 

Small Index Options 

# Listing Time

IpoPeriod 

. NONE 

unknown 

. TODAY 

Listed today 

TOMORROW 

To be listed tomorrow 

. NEXTWEEK 

To be listed next week 

LASTWEEK 

Has been listed last week 

? LASTMONTH 

Has been listed last month 

# Warrant Issuer

Issuer 

. UNKNOW 

unknown 

. SG 

Societe Generale 

. BP 

BNP Paribas 

CS 

Credit Suisse 

CT 

Citi Bank 

EA 

The Bank of East Aisa 

GS 

Goldman Sachs 

HS 

HSBC 

. JP 

JPMorgan Chase 

. MB 

Macquarie Bank 

SC 

Standard Chartered Bank 

. UB 

Union Bank of Switzerland 

. BI 

Bank of China 

DB 

Deutsche Bank 

DC 

Daiwa Bank 

? ML 

Merrill Lynch 

NM 

Nomura Bank 

RB 

Rabobank 

. RS 

The Royal Bank of Scotland 

BC 

Barclays 

. HT 

Haitong Bank 

VT 

Bank Vontobel 

KC 

KBC Bank 

MS 

Morgan Stanley 

GJ 

Guotai Junan 

. XZ 

DBS Bank 

. HU 

Huatai 

KS 

Korea Investment 

. CI 

CITIC Securities 

KL_FIELD 

. ALL 

All 

. DATE_TIME 

Time 

HIGH 

High 

. OPEN 

Open 

. LOW 

Low 

CLOSE 

Close 

LAST_CLOSE 

Close yesterday 

. TRADE_VOL 

Volume 

? TRADE_VAL 

Turnover 

? TURNOVER_RATE 

Turnover rate 

. PE_RATIO 

P/E ratio 

. CHANGE_RATE 

Yield 

# Candlestick Type

KLType 

. NONE 

unknown 

. K_1M 

1 minute candlestick 

. K_DAY 

1 day candlestick 

. K_WEEK 

1 week candlestick 

. K_MON 

1 month candlestick 

K_YEAR 

1 year candlestick 

. K_5M 

5 minutes candlestick 

. K_15M 

15 minutes candlestick 

. K_30M 

30 minutes candlestick 

. K_60M 

60 minutes candlestick 

K_3M 

3 minutes candlestick 

. K_QUARTER 

1 quarter candlestick 

# Period Type

PeriodType 

INTRADAY 

Intraday 

. DAY 

Day 

. WEEK 

Week 

. MONTH 

Month 

# Price Reminder Market Status

PriceReminderMarketStatus 

UNKNOW 

unknown 

OPEN 

Market opens 

US_PRE 

Pre-market of US stocks 

US_AFTER 

After-hours of US stocks 

US_OVERNIGHT 

Overnight trading session of US stocks 

# Watchlist Operation

ModifyUserSecurityOp 

NONE 

Unknown 

. ADD 

Add 

. DEL 

Delete 

? MOVE_OUT 

Remove from group 

# Option Type (by Exercise Time)

OptionAreaType 

. NONE 

unknown 

. AMERICAN 

American Option 

. EUROPEAN 

European Option 

. BERMUDA 

Bermuda Option 

# Option in/out of The Money

OptionCondType 

ALL 

All 

. WITHIN 

In the money 

. OUTSIDE 

Out of the money 

# Option Type (by Direction)

OptionType 

ALL 

all 

CALL 

Call option 

. PUT 

# Plate Set Type

Plate 

? ALL 

All plates 

INDUSTRY 

Industry plate 

. REGION 

Regional plate 

CONCEPT 

Concept plate 

. OTHER 

Other plates 

# Price Reminder Frequency

PriceReminderFreq 

NONE 

Unknown 

ALWAYS 

Keep reminding 

. ONCE_A_DAY 

Once a day 

. ONCE 

Only remind once 

# Price Reminder Type

PriceReminderType 

. NONE 

Unknown 

. PRICE_UP 

Price rise to 

. PRICE_DOWN 

Price fall to 

CHANGE_RATE_UP 

Daily increase rate exceeds 

. CHANGE_RATE_DOWN 

Daily decline rate exceeds 

FIVE_MIN_CHANGE_RATE_UP 

Increate rate in 5 minutes exceeds 

. FIVE_MIN_CHANGE_RATE_DOWN 

Decline rate in 5 minutes exceeds 

VOLUME_UP 

Volume exceeds 

. TURNOVER_UP 

Turnover exceeds 

. TURNOVER_RATE_UP 

Turnover rate exceeds 

. BID_PRICE_UP 

Bid price higher than 

. ASK_PRICE_DOWN 

Ask price lower than 

BID_VOL_UP 

Bid volume higher than 

ASK_VOL_UP 

Ask volume higher than 

. THREE_MIN_CHANGE_RATE_UP 

Increate rate in 3 minutes exceeds 

THREE_MIN_CHANGE_RATE_DOWN 

Decline rate in 3 minutes exceeds 

# Warrant in/out of the Money

PriceType 

. UNKNOW 

Unknown 

OUTSIDE 

Out of the money 

WITH_IN 

In the money 

# Quote Push Type

PushDataType 

UNKNOW 

Unknown 

REALTIME 

Real-time data 

BYDISCONN 

Pull supplementary data (up to 50) during disconnection from Futu server 

CACHE 

Non-real-time non-supplementary data 

# Quote Market

Market 

NONE 

Unknown market 

? HK 

HK market 

. US 

US market 

. SH 

Shanghai market 

. SZ 

Shenzhen market 

. SG 

Singapore market 

. JP 

Japanese market 

AU 

Australian market 

MY 

Malaysian market 

. CA 

Canadian market 

FX 

Forex market 

# Market State

# MarketState

Corresponding time period of each market state, click here to learn more 

NONE 

No trading 

. AUCTION 

Pre-market trading 

WAITING_OPEN 

Waiting for opening 

. MORNING 

Morning session 

. REST 

Lunch break 

AFTERNOON 

Afternoon session / Regular trading hours for U.S stock market 

. CLOSED 

Market closed 

. PRE_MARKET_BEGIN 

Pre-market trading of U.S stock market 

. PRE_MARKET_END 

Pre-market ending of U.S stock market 

. AFTER_HOURS_BEGIN 

After-hours trading of U.S stock market 

AFTER_HOURS_END 

Market closed of U.S. stock market 

. OVERNIGHT 

Overnight trading of U.S. stock market 

NIGHT_OPEN 

Night market trading hours 

. NIGHT_END 

Night market closed 

. NIGHT 

Night market trading hours for U.S. index options 

. TRADE_AT_LAST 

Late trading hours for U.S. index options 

. FUTURE_DAY_OPEN 

Day market trading hours 

FUTURE_DAY_BREAK 

Day market break 

FUTURE_DAY_CLOSE 

Day market closed 

. FUTURE_DAY_WAIT_OPEN 

Futures market wait for opening 

HK_CAS 

After-hours bidding for HK stocks 

. FUTURE_NIGHT_WAIT 

Futures night market wait for opening (Obsolete) 

. FUTURE_AFTERNOON 

Futures afternoon (Obsolete) 

FUTURE_SWITCH_DATE 

Waiting for U.S. futures opening 

FUTURE_OPEN 

Trading hours of U.S. futures 

FUTURE_BREAK 

Break of U.S. futures 

FUTURE_BREAK_OVER 

Trading hours of U.S. futures after break 

. FUTURE_CLOSE 

Market closed of U.S. futures 

. STIB_AFTER_HOURS_WAIT 

After-hours matching period on the Sci-tech innovation plate (Obsolete) 

STIB_AFTER_HOURS_BEGIN 

After-hours trading on the Sci-tech innovation plate begins (Obsolete) 

. STIB_AFTER_HOURS_END 

After-hours trading on the Sci-tech innovation plate ends (Obsolete) 

# US Stock Session

Session 

. NONE 

Unknown 

. RTH 

US Stocks Regular trading hours 

. ETH 

US Stocks Pre/Post $^ +$ regular trading hours 

OVERNIGHT 

US Stocks Overnight trading hours (only applied to Trade API) 

ALL 

# Quote Authorities

QotRight 

? UNKNOW 

Unknown 

. BMP 

BMP (subscription is not supported for this permission) 

LEVEL1 

Level1 

. LEVEL2 

Level2 

. SF 

HK Securities FullTick Quotes 

. NO 

No permission 

# Associated * Data Type

SecurityReferenceType 

UNKNOW 

Unknown 

. WARRANT 

Warrants for stocks 

. FUTURE 

Contracts related to futures main 

# Candlestick Adjustment Type

AuType 

. NONE 

Actual 

. QFQ 

Adjust forward 

. HFQ 

Adjust backward 

# Stock Status

SecurityStatus 

. NONE 

Unknown 

NORMAL 

Normal status 

LISTING 

To be listed 

PURCHASING 

Purchasing 

SUBSCRIBING 

Subscribing 

. BEFORE_DRAK_TRADE_OPENING 

Before the grey market trading opens 

. DRAK_TRADING 

Ongoing grey market trading 

. DRAK_TRADE_END 

Grey market trading closed 

TO_BE_OPEN 

To be open 

. SUSPENDED 

Suspended 

. CALLED 

Called 

EXPIRED_LAST_TRADING_DATE 

Expired latest trading date 

. EXPIRED 

Expired 

. DELISTED 

Delisted 

. CHANGE_TO_TEMPORARY_CODE 

During the company action, the trading was closed and transferred to the temporary code trading 

TEMPORARY_CODE_TRADE_END 

Temporary trading ends 

CHANGED_PLATE_TRADE_END 

Plate changed, the old code is not available for trading 

. CHANGED_CODE_TRADE_END 

The code has been changed, the old code is not available for trading 

RECOVERABLE_CIRCUIT_BREAKER 

Recoverable circuit breaker 

. UN_RECOVERABLE_CIRCUIT_BREAKER 

Unrecoverable circuit breaker 

. AFTER_COMBINATION 

After-hours matchmaking 

. AFTER_TRANSATION 

After-hours trading 

# Stock Type

SecurityType 

. NONE 

Unknown 

. BOND 

Bonds 

BWRT 

Blanket warrants 

STOCK 

Stocks 

. ETF 

ETFs 

WARRANT 

Warrants 

. IDX 

Indexs 

. PLATE 

Plates 

. DRVT 

Options 

PLATESET 

Plate sets 

FUTURE 

Futures 

# Set Price Reminder Operation Type

SetPriceReminderOp 

NONE 

Unknown 

. ADD 

Add 

DEL 

Delete 

ENABLE 

Enable 

DISABLE 

Disable 

. MODIFY 

Modify 

DEL_ALL 

Delete all (delete all price alerts under the specified stock) 

# Sort Direction

SortDir 

. NONE 

Not sorted 

. ASCEND 

Ascending 

? DESCEND 

Descending 

# Sort Field

SortField 

. NONE 

Unknown 

. CODE 

Code 

CUR_PRICE 

Latest price 

. PRICE_CHANGE_VAL 

Price changed 

CHANGE_RATE 

Yield 

STATUS 

Status 

. BID_PRICE 

Bid price 

. ASK_PRICE 

Ask price 

BID_VOL 

Bid volume 

. ASK_VOL 

Ask volume 

. VOLUME 

Volume 

. TURNOVER 

Turnover 

AMPLITUDE 

Amplitude 

. SCORE 

Comprehensive score 

PREMIUM 

Premium 

? EFFECTIVE_LEVERAGE 

Effective leverage 

. DELTA 

Hedging value 

. IMPLIED_VOLATILITY 

Implied volatility 

. TYPE 

Type 

. STRIKE_PRICE 

Strike price 

. BREAK_EVEN_POINT 

Break even point 

? MATURITY_TIME 

Maturity date 

LIST_TIME 

Listing date 

LAST_TRADE_TIME 

Lastest trading day 

. LEVERAGE 

Leverage ratio 

IN_OUT_MONEY 

In/out of the money % 

. RECOVERY_PRICE 

Recovery price 

CHANGE_PRICE 

Change price 

CHANGE 

Change ratio 

. STREET_RATE 

Outstanding percentage (the propotioin of retail investors) 

STREET_VOL 

Outstanding quantity (the volume held by retail investors) 

WARRANT_NAME 

Warrant name 

ISSUER 

Issuer 

. LOT_SIZE 

Lot size 

. ISSUE_SIZE 

Issue size 

. UPPER_STRIKE_PRICE 

Upper bound 

LOWER_STRIKE_PRICE 

Lower bound 

. INLINE_PRICE_STATUS 

In/out of bounds 

PRE_CUR_PRICE 

Latest price of pre-market 

. AFTER_CUR_PRICE 

Latest price of after-hours 

. PRE_PRICE_CHANGE_VAL 

Pre-market changes 

AFTER_PRICE_CHANGE_VAL 

After-hours changes 

. PRE_CHANGE_RATE 

Pre-market change rate % 

. AFTER_CHANGE_RATE 

After-hours change rate % 

. PRE_AMPLITUDE 

Pre-market amplitude % 

. AFTER_AMPLITUDE 

After-hours amplitude % 

PRE_TURNOVER 

Pre-market turnover 

. AFTER_TURNOVER 

After-hours turnover 

. LAST_SETTLE_PRICE 

Last settle price 

. POSITION 

Position 

. POSITION_CHANGE 

Daily increase of position 

# Simple Filter Properties

StockField 

. NONE 

unknown 

. STOCK_CODE 

Stock code, does not accept list inputs as an interval 

STOCK_NAME 

Stock name, does not accept list inputs as an interval 

. CUR_PRICE 

The latest price 

. CUR_PRICE_TO_HIGHEST52_WEEKS_RATIO 

(CP - WH52) / WH52 

CP: Current price 

WH52: 52-week high 

Corresponding to the “percentage from 52-week high” on the PC terminal 

. CUR_PRICE_TO_LOWEST52_WEEKS_RATIO 

(CP - WL52) / WL52 

CP: Current price 

WL52: 52-week low 

Corresponding to the “percentage from 52-week low” on the PC terminal 

. HIGH_PRICE_TO_HIGHEST52_WEEKS_RATIO 

(TH - WH52) / WH52 

TH: Today's high 

WH52: 52-week high 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/637c4f8fa88f7b04f5032c61a383353b7ba1063aaa3ea9d4d294883a6b835a06.jpg)


LOW_PRICE_TO_LOWEST52_WEEKS_RATIO 

(TL - WL52) / WL52 

TL: Today's low 

WL52: 52-week low 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/60756c29aa49be6713ae7d935cc58030cb0235a0035f7b163a0523914146f6d7.jpg)


VOLUME_RATIO 

Volume ratio 

. BID_ASK_RATIO 

Bid-ask ratio 

LOT_PRICE 

Price per lot 

MARKET_VAL 

Market value 

PE_ANNUAL 

Trailing P/E 

PE_TTM 

P/E TTM 

. PB_RATE 

P/B ratio 

. CHANGE_RATE_5MIN 

Change rate in 5 minutes 

. CHANGE_RATE_BEGIN_YEAR 

Price change rate from this year 

PS_TTM 

P/S TTM 

PCF_TTM 

PCF TTM 

. TOTAL_SHARE 

Total number of shares 

FLOAT_SHARE 

Shares outstanding 

. FLOAT_MARKET_VAL 

Market value outstanding 

# Subscription Type

SubType 

NONE 

Unknown 

. QUOTE 

Basic quote 

. ORDER_BOOK 

Order book 

. TICKER 

Tick-by-tick 

. RT_DATA 

Time Frame 

K_DAY 

Daily candlesticks 

K_5M 

5 minutes candlesticks 

. K_15M 

15 minutes candlesticks 

K_30M 

30 minutes candlesticks 

K_60M 

60 minutes candlesticks 

. K_1M 

1 minute candlesticks 

. K_WEEK 

Weekly candlesticks 

. K_MON 

Monthly candlesticks 

. BROKER 

Broker's queue 

K_QURATER 

Seasonal candlesticks 

. K_YEAR 

Annual candlesticks 

? K_3M 

3 minutes candlesticks 

# Transaction Direction

TickerDirect 

. NONE 

unknown 

. BUY 

Active buy 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/6cbdd4d17687f6bd2acf438d6a04eeb7a5149bc938c738e53e9cd0f02caef6d3.jpg)


. SELL 

Active sell 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/03b7297b5f564af7cb5f5d4ef7f34056a91b1b5787bf5ec7cc70e71ae71a81c1.jpg)


NEUTRAL 

Neutral transaction 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/21a68568991f0892ef795dca5f7af81a2a004dd38c66dbb4d01d20412d08091e.jpg)


# Tick-by-Tick Transaction Type

TickerType 

. UNKNOWN 

Unknown 

. AUTO_MATCH 

Regular sale 

LATE 

Pre-market trade 

. NON_AUTO_MATCH 

Non-regular sale 

INTER_AUTO_MATCH 

Regular sale for same broker 

. INTER_NON_AUTO_MATCH 

Non-regular sale for same broker 

ODD_LOT 

Odd lot trade 

AUCTION 

Auction trade 

BULK 

Bunched trade 

. CRASH 

Cash trade 

CROSS_MARKET 

Intermarket sweep 

. BULK_SOLD 

Bunched sold trade 

FREE_ON_BOARD 

Price variation trade 

RULE127_OR155 

Rule 127 (NYSE only) or Rule 155 (NYSE MKT only) 

. DELAY 

Delay the transaction 

? MARKET_CENTER_CLOSE_PRICE 

Market center close price 

NEXT_DAY 

Next day 

. MARKET_CENTER_OPENING 

Market center opening trade 

. PRIOR_REFERENCE_PRICE 

Prior reference price 

. MARKET_CENTER_OPEN_PRICE 

Market center open price 

SELLER 

Seller 

T 

Form T(pre-open and post-close market trade) 

EXTENDED_TRADING_HOURS 

Extended trading hours/sold out of sequence 

CONTINGENT 

Contingent trade 

. AVERAGE_PRICE 

Average price trade 

. OTC_SOLD 

Sold(out of sequence) 

ODD_LOT_CROSS_MARKET 

Odd lot cross trade 

DERIVATIVELY_PRICED 

Derivatively priced 

REOPENINGP_RICED 

Re-Opening price 

. CLOSING_PRICED 

Closing price 

. COMPREHENSIVE_DELAY_PRICE 

Consolidated late price per listing packet 

. OVERSEAS 

One party to the transaction is not a member of the Hong Kong Stock Exchange and is an over-the-counter transaction 

# Check The Market on The Trading Day

TradeDateMarket 

NONE 

Unknown 

. HK 

HK market 

US 

US market 

. CN 

A-share market 

. NT 

Northbound Trading 

. ST 

Southbound Trading 

JP_FUTURE 

Japanese future market 

. SG_FUTURE 

Singapore future market 

# Type of Trading Day

TradeDateType 

WHOLE 

Whole day trading 

. MORNING 

Trading in the morning, closed in the afternoon 

. AFTERNOON 

Trading in the afternoon, closed in the morning 

# Warrant Status

WarrantStatus 

NONE 

Unknown 

. NORMAL 

Normal status 

. SUSPEND 

Suspended 

. STOP_TRADE 

Stop trading 

. PENDING_LISTING 

Waiting to be listed 

# Warrant Type

WrtType 

. NONE 

Unknown 

. CALL 

Long warrants 

. PUT 

Short warrants 

BULL 

Call warrants 

BEAR 

Put warrants 

INLINE 

Inline Warrants 

# Exchange Type

ExchType 

. NONE 

Unknown 

. HK_MAINBOARD 

HKEx·Main Board 

. HK_GEMBOARD 

HKEx·GEM 

HK_HKEX 

HKEx 

. US_NYSE 

NYSE 

? US_NASDAQ 

NASDAQ 

US_PINK 

OTC Mkt 

. US_AMEX 

AMEX 

US_OPTION 

US 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/79fe5b642abbb57fde37d65e0a028ff65475da80e282fdeb7bc283d9e85dfe86.jpg)


US_NYMEX 

NYMEX 

. US_COMEX 

COMEX 

US_CBOT 

CBOT 

US_CME 

CME 

. US_CBOE 

CBOE 

. CN_SH 

SH Stock Ex 

CN_SZ 

SZ Stock Ex 

CN_STIB 

STAR 

SG_SGX 

SGX 

JP_OSE 

OSE 

# Security Identification

Security 

message Security   
{ required int32 market $= 1$ //QotMarket, quote market required string code $= 2$ //Code 

# Candlestick data


KLine


1 message KLine   
2 {   
3 required string time $= 1$ ; //String of timestamp (Format: yyyy-MM-dd HH:mm:ss)   
4 required bool isBlank $= 2$ ; //Whether it is a point with empty content, if it   
5 optional double highPrice $= 3$ ; //High   
6 optional double openPrice $= 4$ ; //Open   
7 optional double lowPrice $= 5$ ; //Low   
8 optional double closePrice $= 6$ ; //Close   
9 optional double lastClosePrice $= 7$ ; //Close yesterday   
10 optional int64 volume $= 8$ ; //Volume   
11 optional double turnover $= 9$ ; //Turnover   
12 optional double turnoverRate $= 10$ ; //Turnover rate (this field is in decimal)   
13 optional double pe $= 11$ ; //P/E ratio   
14 optional double changeRate $= 12$ ; //Yield (This field is in percentage form, s)   
15 optional double timestamp $= 13$ ; //Timestamp   
16 } 

# Option Specific Fields of The Underlying Quote


OptionBasicQotExData


1 message OptionBasicQotExData   
2 {   
3 required double strikePrice $= 1$ ;//Strike price   
4 required int32 contractSize $= 2$ //Contract size (integer)   
5 optional double contractSizeFloat $= 17$ ; //Contract size(float) 

6 required int32 openInterest $= 3$ //Number of open positions   
7 required double impliedVolatility $= 4$ //Implied volatility (This field is in   
8 required double premium $= 5$ //Premium (This field is in percentage form, so   
9 required double delta $= 6$ //Greek value Delta   
10 required double gamma $= 7$ //Greek value Gamma   
11 required double vega $= 8$ //Greek value Vega   
12 required double theta $= 9$ //Greek value Theta   
13 required double rho $= 10$ //Greek value Rho   
14 optional int32 netOpenInterest $= 11$ //Net open contract number , only HK opt   
15 optional int32 expiryDateDistance $= 12$ //The number of days from the expiry   
16 optional double contractNominalValue $= 13$ //Contract nominal amount , only H   
17 optional double ownerLotMultiplier $= 14$ //Equal number of underlying stocks   
18 optional int32 optionAreaType $= 15$ //OptionAreaType, option type (by exercis   
19 optional double contractMultiplier $= 16$ //Contract multiplier   
20 optional int32 indexOptionType $= 18$ //Qot/Common.IndexOptionType, index opt   
21 } 

# Futures Specific Fields of The Base Quote


FutureBasicQotExData


1 message FutureBasicQotExData   
2 {   
3 required double lastSettlePrice $= 1$ ; //Close yesterday   
4 required int32 position $= 2$ ; //Hold position   
5 required int32 positionChange $= 3$ ; //Daily change in position   
6 optional int32 expiryDateDistance $= 4$ ; //The number of days from the expirat 

# Basic Quotation


BasicQot


1 message BasicQot   
2 {   
3 required Security security $= 1$ //Stock   
4 optional string name $= 24$ // stock name   
5 required bool isSuspended $= 2$ //whether trading is suspended 

6 required stringptime $= 3$ //listed date string(This field is deprecated   
7 required double priceSpread $= 4$ //Spread   
8 required stringupdateTime $= 5$ //Update time string of the latest price (For   
9 required double highPrice $= 6$ //High   
10 required double openPrice $= 7$ //Open   
11 required double lowPrice $= 8$ //low   
12 required double curPrice $= 9$ //The latest price   
13 required double lastClosePrice $= 10$ //Close yesterday   
14 required int64 volume $= 11$ //Volume   
15 required double turnover $= 12$ //Turnover   
16 required double turnoverRate $= 13$ //Turnover rate (This field is in percenta   
17 required double amplitude $= 14$ //Amplitude (This field is in percentage for   
18 optional int32 darkStatus $= 15$ //Grey market trading status   
19 optional OptionBasicQotExData optionExData $= 16$ //Option specific field   
20 optional double listTimestamp $= 17$ //Time stamp of listing date (This field   
21 optional double updateTimestamp $= 18$ //Update timestamp of the latest price   
22 optional PreAfterMarketData preMarket $= 19$ //Pre-market data   
23 optional PreAfterMarketData afterMarket $= 20$ //After-hours data   
24 optional int32 secStatus $= 21$ //Security status   
25 optional FutureBasicQotExData futureExData $= 22$ //Futures specific field   
26 } 

# Before And After Data


PreAfterMarketData


1 //US stocks support pre-market and after-hours data   
2 //The Sci-tech Innovation Plate only supports after-hours data: trading volume,   
3 message PreAfterMarketData   
4 {   
5 optional double price $= 1$ ;//Pre-market or after-hours## Price   
6 optional double highPrice $= 2$ ;//Pre-market or after-hours## High   
7 optional double lowPrice $= 3$ ;//Pre-market or after-hours## Low   
8 optional int64 volume $= 4$ ;//Pre-market or after-hours## Volume   
9 optional double turnover $= 5$ ;//Pre-market or after-hours##Turnover   
10 optional double changeVal $= 6$ ;//Pre-market or after-hours## Change in price   
11 optional double changeRate $= 7$ ;//Pre-market or after-hours##Yield (This field   
12 optional double amplitude $= 8$ ;//Pre-market or after-hours## Amplitude (This   
13 } 


TimeShare


1 message TimeShare   
2 {   
3 required string time $= 1$ ; //Time string (Format: yyyy-MM-dd HH:mm:ss)   
4 required int32 minute $= 2$ ; //Minutes after 0 o'clock   
5 required bool isBlank $= 3$ ; //Whether the content is empty, if true, it conte   
6 optional double price $= 4$ ; //Current price   
7 optional double lastClosePrice $= 5$ ; //Close yesterday   
8 optional double avgPrice $= 6$ ; //Average price   
9 optional int64 volume $= 7$ ; //Volume   
10 optional double turnover $= 8$ ; //Turnover   
11 optional double timestamp $= 9$ ; //Timestamp   
12 } 

# Basic Static Information of Securities


SecurityStaticBasic


```txt
1   
2   
3   
4   
5   
6   
7   
8   
9   
10   
11   
12   
13 
```

# Warrant Additional Static Information


WarrantStaticExData


1 message WarrantStaticExData   
2 {   
3 required int32 type $= 1$ ; //Qot/Common.WarrantType, Warrant Type   
4 required Qot/Common.Security owner $= 2$ ; //The underlying stock   
5 } 

# Option Additional Static Information


OptionStaticExData


1 message OptionStaticExData   
2 {   
3 required int32 type $= 1$ //Qot/Common.OptionType, option   
4 required Qot/Common.Security owner $= 2$ //Underlying stock   
5 required string strikeTime $= 3$ //Exercise date (Format: yyyy-MM-dd)   
6 required double strikePrice $= 4$ //Strike price   
7 required bool suspend $= 5$ //Suspended or not   
8 required string market $= 6$ //Issuance market name   
9 optional double strikeTimestamp $= 7$ //Exercise date timestamp   
10 optional int32 indexOptionType $= 8$ //Qot/Common.IndexOptionType, type of int   
11 optional int32 expirationCycle $= 9$ // Qot/CommonExpirationCycle, type of option   
12 optional int32 optionStandardType $= 10$ // Qot/Common.OptionStandardType, type of option   
13 optional int32 optionSettlementMode $= 11$ // OptionSettlementMode, mode of option 

# Additional Static Information About Futures


FutureStaticExData


message FutureStaticExData 

required string lastTradeTime = 1; //The lastest trading day, only future no optional double lastTradeTimestamp = 2; //The lastest trading day timestamp, required bool isMainContract = 3; //Futures main contract or not 

# Securities Static Information

# SecurityStaticInfo

message SecurityStaticInfo 

required SecurityStaticBasic basic = 1; //Basic security information optional WarrantStaticExData warrantExData = 2; //Additional information for optional OptionStaticExData optionExData = 3; //Additional information for o optional FutureStaticExData futureExData = 4; //Additional information for f 

# Brokerage

# Broker

message Broker 

required int64 id = 1; //Broker ID required string name = 2; //Broker name required int32 pos = 3; //Broker position //The following fields are specific to SF quote optional int64 orderID = 4; //Exchange order ID, which is different from the optional int64 volume = 5; //Number of shares in order 


Ticker


1 message Ticker   
2 {   
3 required string time $= 1$ ; //Time string (Format: yyyy-MM-dd HH:mm:ss)   
4 required int64 sequence $= 2$ ; //Unique identification   
5 required int32 dir $= 3$ ; //TickerDirection, buy or sell direction   
6 required double price $= 4$ ; //Price   
7 required int64 volume $= 5$ ; //Volume   
8 required double turnover $= 6$ ; // turnover   
9 optional double recvTime $= 7$ ; //Local timestamp of received push data, used   
10 optional int32 type $= 8$ ; //TickerType, type by pen   
11 optional int32 typeSign $= 9$ ; //Pattern-by-stroke type sign   
12 optional int32 pushDataType $= 10$ ; //Used to distinguish push situations, this   
13 optional double timestamp $= 11$ ; //time stamp}   
14 } 

# Transaction File Details


OrderBookDetail


1 message OrderBookDetail   
2 {   
3 required int64 orderID $= 1$ ; //Exchange order ID, which is different from the   
4 required int64 volume $= 2$ ; //Number of shares in order   
5 } 

# Order Book


OrderBook


message OrderBook   
{ required double price $= 1$ //Order price required int64 volume $= 2$ //Order quantity required int32 orederCount $= 3$ //Number of commissioned orders repeated OrderBookDetail detailList $= 4$ //Order information, unique to HK S 

# Changes in Holdings


ShareHoldingChange


message ShareHoldingChange   
{ required string holderName $= 1$ //Holder name (institution name or fund name required double holdingQty $= 2$ //Current number of holdings required double holdingRatio $= 3$ //Current shareholding percentage (This file required double changeQty $= 4$ //The number of changes from the previous time required double changeRatio $= 5$ //The percentage of change from the last time required string time $= 6$ //Release time (Format: yyyy-MM-dd HH:mm:ss) optional double timestamp $= 7$ //Timestamp   
} 

# Single Subscription Type Information


SubInfo


message SubInfo   
{ required int32(SubType $= 1$ //Qot/Common.SubType, subscription type repeated Qot/Common.Security securityList $= 2$ //Subscribe to securities of } 

# Single Connection Subscription Information


ConnSubInfo


1 message ConnSubInfo   
2 {   
3 repeated SubInfo subInfoList $= 1$ ; //The connection subscription information   
4 required int32 usedQuota $= 2$ ; //The subscription quota that the connection has   
5 required bool isOwnConnData $= 3$ ; //Used to distinguish whether it is self-conn   
6 } 

# Plate Information


PlateInfo


1 message PlateInfo   
2 {   
3 required Qot/Common.Security plate $=$ 1; //Plate   
4 required string name $= 2$ ;//Plate name   
5 optional int32plateType $=$ 3; //Plate type, only 3207 (to get the plate to w 

# Adjustment Information


Rehab


1 message Rehab   
2 {   
3 required string time $= 1$ ; //Time string (Format: yyyy-MM-dd)   
4 required int64 companyActFlag $= 2$ ; //CompanyAct combination flag bit, which   
5 required double fwdFactorA $= 3$ ; //Adjustments factor A   
6 required double fwdFactorB $= 4$ ; //Adjustments factor B 

```txt
7 required double bwdFactorA = 5; //Adjustments factor A  
8 required double bwdFactorB = 6; //Adjustments factor B  
9 optional int32 splitBase = 7; //Stock split (for example, 1 split 5, Base is  
10 optional int32 splitErt = 8;  
11 optional int32 joinBase = 9; //Reverse stock split (for example, 50 in 1, Base  
12 optional int32 joinErt = 10;  
13 optional int32 bonusBase = 11; //Bonus shares (for example, 10 free 3, Base  
14 optional int32 bonusErt = 12;  
15 optional int32 transferBase = 13; //Transfer bonus shares (for example, 10 to  
16 optional int32 transferErt = 14;  
17 optional int32 allotBase = 15; //Allotment (for example, 10 get 2 free, allot  
18 optional int32 allotErt = 16;  
19 optional double allotPrice = 17;  
20 optional int32 addBase = 18; //Additional shares (for example, 10 get 2 free)  
21 optional int32 addErt = 19;  
22 optional double addPrice = 20;  
23 optional double dividend = 21; //Cash dividend (for example, if every 10 share  
24 optional double spDividend = 22; //Special dividend (for example, if a specia  
25 optional double timestamp = 23; //Timestamp  
26} 
```

For CompanyAct combination flag bit, refer to CompanyAct. 

# Expiration Cycle

ExpirationCycle 

. NONE 

Unknown 

. WEEK 

Weekly options 

MONTH 

Monthly options 

. END_OF_MONTH 

End-Of-Monthly options 

QUARTERLY 

Quarterly options 

. WEEKMON 

Monthly options-Monday 

. WEEKTUE 

Monthly options-Tuesday 

WEEKWED 

Monthly options-Wednesday 

. WEEKTHU 

Monthly options-Thursday 

. WEEKFRI 

Monthly options-Friday 

# Option Standard Type

OptionStandardType 

. NONE 

Unknown 

STANDARD 

standard options 

. NON_STANDARD 

non-standard options 

# Option Settlement Mode

OptionSettlementMode 

NONE 

Unknown 

. AM 

Asian Pricing 

PM 

Path-Dependent 

## Stockholder (Deprecated) 

# Stock Holder

StockHolder 

. NONE 

Unknown 

INSTITUTE 

Institute 

FUND 

Fund 

. EXECUTIVE 

Executives 

# Overview

<table><tr><td>Module</td><td>Interface Name</td><td>Function Description</td></tr><tr><td rowspan="2">Account</td><td>get_acc_list</td><td>Get account list</td></tr><tr><td>unlock_trade</td><td>Unlock trading</td></tr><tr><td rowspan="5">Asset and Position</td><td>accinfo_query</td><td>Get account financial information</td></tr><tr><td>acctradinginfo_query</td><td>Get maximum tradable quantity</td></tr><tr><td>position_list_query</td><td>Get positions list</td></tr><tr><td>Trd_GetMarginRatio</td><td>Get margin data</td></tr><tr><td>Get Cash Flow Summary</td><td>Get Account Cash Flow Data</td></tr><tr><td rowspan="7">Order</td><td>place_order</td><td>Place order</td></tr><tr><td>modify_order</td><td>Modify or cancel order</td></tr><tr><td>order_list_query</td><td>Get order list</td></tr><tr><td>order_fee_query</td><td>Get order fees</td></tr><tr><td>history_order_list_query</td><td>Get historical order list</td></tr><tr><td>TradeOrderHandlerBase</td><td>Order callback</td></tr><tr><td>SubAccPush</td><td>Trade data callback</td></tr><tr><td rowspan="3">Deal</td><td>deal_list_query</td><td>Get today&#x27;s executed trades</td></tr><tr><td>historyDeal_list_query</td><td>Get historical executed trades</td></tr><tr><td>TradeDealHandlerBase</td><td>Trade execution callback</td></tr></table>

# Transaction Objects

# Create the connection

OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $= 127.0.0.1$ port $= 11111$ , is_encrypt $\equiv$ None, security_firm $\equiv$ SecurityFirm.FUTUSECURITIES) 

```python
OpenFutureTradeContext(host='127.0.0.1', port=11111, is Encrypt=None, security_firm=SecurityFirm.FUTUSESECURITIES) 
```

# Description

According to the transaction variaties, select a correct account, and create its transaction object. 

<table><tr><td>Transaction Objects</td><td>Accounts</td></tr><tr><td>OpenSecTradeContext</td><td>Securities account</td></tr><tr><td>OpenFutureTradeContext</td><td>Futures account</td></tr></table>

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>filter_trdmarket</td><td>TrdMarket</td><td>Filter accounts according to the transaction market authority.</td></tr><tr><td>host</td><td>str</td><td>The IP listened by OpenD.</td></tr><tr><td>port</td><td>int</td><td>The port listened by OpenD.</td></tr><tr><td>is_encrypt</td><td>bool</td><td>Whether to enable encryption.</td></tr><tr><td>security_firm</td><td>SecurityFirm</td><td>Specified security firm</td></tr></table>

# Example

1 from futu import ? 

2 trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host='127.0.0.1', p 

3 trd_ctx.close() # After using the connection, remember to close it to prevent the 

# Close the connection

# close()

# Description

Close the trading object. By default, the threads created inside the Futu API will prevent the process from exiting, and the process can exit normally only after all Contexts are closed. But through set_all_thread_daemon, all internal threads can be set as daemon threads. At this time, even if close of Context is not called, the process can exit normally. 

# Example

1 from futu import * 

2 trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host='127.0.0.1', p 

3 trd_ctx.close() # After using the connection, remember to close it to prevent the 

# Get the List of Trading Accounts

get_acc_list() 

. Description 

Get a list of trading accounts. Before calling other trading interfaces, please obtain this list first and confirm that the trading account to be operated is correct. 

Parameters 

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, trading account list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Trading account list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_type</td><td>TrdAccType</td><td>Account type.</td></tr><tr><td>uni_card_num</td><td>str</td><td>Universal account number, same as the display in the mobile terminal.</td></tr><tr><td>card_num</td><td>str</td><td>Trading account number</td></tr><tr><td>sim_acc_type</td><td>SimAccType</td><td>Simulate account type.</td></tr><tr><td>security_firm</td><td>SecurityFirm</td><td>Securities firm to which the account belongs.</td></tr><tr><td>trdmarket_auth</td><td>list</td><td>Transaction market authority.</td></tr><tr><td>acc_status</td><td>TrdAccStatus</td><td>Account status.</td></tr><tr><td>acc-role</td><td>TrdAccRole</td><td>Account Structure</td></tr><tr><td>jp_acc_type</td><td>list</td><td>JP sub account type</td></tr></table>

# . Description

After the paper trading of HK/US stock options is opened, this function will return 2 paper trading accounts when obtaining the list of HK/US trading accounts. The first one is the original account, and the second one is the option paper trading account. Currently, the US paper trading accounts from OpenAPI are different with those showed on the mobile app. Click here for more details. 

# Example

1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $= 127.0.0.1$ ,pc   
3 ret，data $=$ trdctx.get_acc_list()   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 print(data['acc_id'][0]) #Get the first account ID   
7 print(data['acc_id'].values.tolist()) # convert to list   
8 else:   
9 print('get_acc_list error:'，data)   
10 trdCtx.close() 

# Output

```txt
1 acc_id trd_env acc_type uni_card_num card_num 2 0 281756479345015383 REAL MARGIN 1001289516908051 1001329805025007 3 1 8377516 SIMULATE CASH N/A N/A 4 2 10741586 SIMULATE MARGIN N/A N/A 5 3 281756455983234027 REAL MARGIN N/A 1001100321720699 
```

6 281756479345015383 

7 [281756479345015383, 8377516, 10741586, 281756455983234027] 

# Unlock Trade

unlock_trade(password=None, password_md5=None, is_unlock=True) 

Description 

Lock or unlock trade 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>password</td><td>str</td><td>Transaction password.</td></tr><tr><td>password_md5</td><td>str</td><td>32-bit MD5 encryption of transaction password (all lowercase).</td></tr><tr><td>is_unlock</td><td>bool</td><td>Lock or unlock.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">msg</td><td>NONE</td><td>If ret == RET_OK, None is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Example 

1 from futu import \*   
2 pwd_unlock $=$ '123456'   
3 trdctx $=$ OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host $=$ 127.0.0.1', p   
4 ret, data $=$ trdctx.unlock_trade(pwd_unlock)   
5 if ret $= =$ RET_OK:   
6 print('unlock success!')   
7 else: 

8 print('unlock_trade failed: ', data) 

trd_ctx.close() 

# Output

1 unlock success! 

# TIP

When using live trading accounts, you need to unlock trade before calling Place Order or Modify or Cancel Orders interface, but when using paper trading accounts, you do not need to unlock trade. 

Locking or unlocking the transaction is an operation on OpenD. As long as one connection is unlocked, all other connections can call the transaction interface 

It is strongly recommended that customers who connect to OpenD via the external network for live trading use encrypted channels, refer to Enable protocol encryption 

OpenAPI does not support Futu token. If you have activated Futu token, it will fail to unlock. You need to turn off the token and then use OpenAPI to unlock. 

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single user ID. 

# Get Account Funds

accinfo_query(trd_env=TrdEnv.REAL, acc_id=0, acc_index=0, refresh_cache=False, currency=Currency.HKD, asset_category=AssetCategory.NONE) 

# . Description

Query fund data such as net asset value, securities market value, cash, and purchasing power of trading accounts. 

# ? Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>refresh_cache</td><td>bool</td><td>Whether to refresh the cache.</td></tr><tr><td>currency</td><td>Currency</td><td>The display currency of the funds.</td></tr><tr><td>asset_category</td><td>AssetCategory</td><td>Asset category</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, fund data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>power</td><td>float</td><td>Maximum Buying Power.</td></tr><tr><td>max_power_short</td><td>float</td><td>Short Buying Power.</td></tr><tr><td>net_cash_power</td><td>float</td><td>Cash Buying Power.</td></tr><tr><td>total_assets</td><td>float</td><td>Total Net Assets.</td></tr><tr><td>securities_assets</td><td>float</td><td>Security Assets.</td></tr><tr><td>fund_assets</td><td>float</td><td>Fund Assets.</td></tr><tr><td>bond_assets</td><td>float</td><td>Bond Assets.</td></tr><tr><td>cash</td><td>float</td><td>Cash.</td></tr><tr><td>market_val</td><td>float</td><td>Securities Market Value.</td></tr><tr><td>long_mv</td><td>float</td><td>Long Market Value.</td></tr><tr><td>short_mv</td><td>float</td><td>Short Market Value.</td></tr><tr><td>pending_asset</td><td>float</td><td>Asset in Transit.</td></tr><tr><td>interest Charged_amount</td><td>float</td><td>Interest Charged Amount.</td></tr><tr><td>frozen_cash</td><td>float</td><td>Funds on Hold.</td></tr><tr><td>avl_withdrawal_cash</td><td>float</td><td>Withdrawable Cash.</td></tr><tr><td>max_withdrawal</td><td>float</td><td>Maximum Withdrawal.</td></tr><tr><td>currency</td><td>Currency</td><td>The currency used for this query.</td></tr><tr><td>available_funds</td><td>float</td><td>Available funds.</td></tr><tr><td>unrealized_pl</td><td>float</td><td>Unrealized gain or loss.</td></tr><tr><td>realized_pl</td><td>float</td><td>Realized gain or loss.</td></tr><tr><td>risk_level</td><td>CltRiskLevel</td><td>Risk control level.</td></tr><tr><td>risk_status</td><td>CltRiskStatus</td><td>Risk status.</td></tr><tr><td>initial_margin</td><td>float</td><td>Initial Margin.</td></tr><tr><td>margin_call_margin</td><td>float</td><td>Margin-call Margin.</td></tr><tr><td>maintenance_margin</td><td>float</td><td>Maintenance Margin.</td></tr><tr><td>hk_cash</td><td>float</td><td>HKD Cash.</td></tr><tr><td>hk_avl_withdrawal_cash</td><td>float</td><td>HKD Withdrawable Cash.</td></tr><tr><td>hkd_net_cash_power</td><td>float</td><td>HKD Cash Buying Power.</td></tr><tr><td>hkd_assets</td><td>float</td><td>HK Net Assets Value.</td></tr><tr><td>us_cash</td><td>float</td><td>USD Cash.</td></tr><tr><td>us_avl_withdrawal_cash</td><td>float</td><td>USD Withdrawable Cash.</td></tr><tr><td>usd_net_cash_power</td><td>float</td><td>USD Cash Buying Power.</td></tr><tr><td>usd_assets</td><td>float</td><td>US Net Assets Value.</td></tr><tr><td>cn_cash</td><td>float</td><td>CNH Cash.</td></tr><tr><td>cn_avl_withdrawal_cash</td><td>float</td><td>CNH Withdrawable Cash.</td></tr><tr><td>cnh_net_cash_power</td><td>float</td><td>CNH Cash Buying Power.</td></tr><tr><td>cnh_assets</td><td>float</td><td>CN Net Assets Value.</td></tr><tr><td>jp_cash</td><td>float</td><td>JPY Cash.</td></tr><tr><td>jp_avl_withdrawal_cash</td><td>float</td><td>JPY Withdrawable Cash.</td></tr><tr><td>jpy_net_cash_power</td><td>float</td><td>JPY Cash Buying Power.</td></tr><tr><td>jpy_assets</td><td>float</td><td>JP Net Assets Value.</td></tr><tr><td>sg_cash</td><td>float</td><td>SGD Cash.</td></tr><tr><td>sg_avl_withdrawal_cash</td><td>float</td><td>SGD Withdrawable Cash.</td></tr><tr><td>sgd_net_cash_power</td><td>float</td><td>SGD Cash Buying Power.</td></tr><tr><td>sgd_assets</td><td>float</td><td>SG Net Assets Value.</td></tr><tr><td>au_cash</td><td>float</td><td>AUD Cash.</td></tr><tr><td>au_avl_withdrawal_cash</td><td>float</td><td>AUD Withdrawable Cash.</td></tr><tr><td>aud_net_cash_power</td><td>float</td><td>AUD Cash Buying Power.</td></tr><tr><td>aud_assets</td><td>float</td><td>AU Net Assets Value.</td></tr><tr><td>ca_cash</td><td>float</td><td>CAD Cash.</td></tr><tr><td>ca_avl_withdrawal_cash</td><td>float</td><td>CAD Withdrawable Cash.</td></tr><tr><td>cad_net_cash_power</td><td>float</td><td>CAD Cash Buying Power.</td></tr><tr><td>cad_assets</td><td>float</td><td>CA Net Assets Value.</td></tr><tr><td>my_cash</td><td>float</td><td>MYR Cash.</td></tr><tr><td>my_avl_withdrawal_cash</td><td>float</td><td>MYR Withdrawable Cash.</td></tr><tr><td>myr_net_cash_power</td><td>float</td><td>MYR Cash Buying Power.</td></tr><tr><td>myr_assets</td><td>float</td><td>MY Net Assets Value.</td></tr><tr><td>is_pdt</td><td>bool</td><td>Is it marked as a PDT.</td></tr><tr><td>pdt_seq</td><td>string</td><td>Day Trades Left.</td></tr><tr><td>beginning_dtbp</td><td>float</td><td>Beginning DTBP.</td></tr><tr><td>remaining_dtbp</td><td>float</td><td>Remaining DTBP.</td></tr><tr><td>dt_call_amount</td><td>float</td><td>Day-trading Call Amount.</td></tr><tr><td>dt.status</td><td>DtStatus</td><td>Day-trading Status.</td></tr></table>

# . Example

1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host $= 127.0.0.1$ ,pc   
3 ret，data $=$ trdctx.accinfo_query()   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 print(data['power'] [0]) #Get the first buying power   
7 print(data['power'].values.tolist()) # convert to list   
8 else:   
9 print('accinfo_query error:'，data)   
10 trdctx.close() # Close the current connection 

# . Output

```tcl
1 power max_power_short net_cash_power total_assets securities_assets fund_asset  
2 0 465453.903307 465453.903307 0.0 289932.0404 197028.220  
3 465453.903307  
4 [465453.903307] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

It will be restricted by the frequency limit for this interface, only when refresh_cache is True 

# Query the Maximum Quantity that Can be Bought or Sold

acctradinginfo_query(order_type, code, price, order_id=None, 

adjust_limit ${ \bf \Pi } = \theta$ , trd_env=TrdEnv.REAL, acc_id ${ \tt = } 0$ , acc_index $\cdot$ , 

session $\cdot$ Session.NONE, jp_acc_type $^ { 1 } =$ SubAccType.JP_GENERAL, position_id=NONE) 

# . Description

Query the maximum quantity that can be bought or sold under a specifictrading account, and you can also query the maximum changeable quantity of a specific order under a specifictrading account. 

Cash account request options are not supported. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>order_type</td><td>OrderType</td><td>Order type.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>price</td><td>float</td><td>Quotation.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>adjust_limit</td><td>float</td><td>Price adjustment range.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>session</td><td>Session</td><td>US stocks Trading Session</td></tr><tr><td>jp_acc_type</td><td>SubAccType</td><td>JP sub account type</td></tr><tr><td>position_id</td><td>int</td><td>Position ID</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, account list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Account list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>max_cash_buy</td><td>float</td><td>Buy on cash.</td></tr><tr><td>max_cash_and_margin_buy</td><td>float</td><td>Buy on margin.</td></tr><tr><td>max_position_buy</td><td>float</td><td>Sell on position.</td></tr><tr><td>max_buy_short</td><td>float</td><td>Short sell.</td></tr><tr><td>max_buy_back</td><td>float</td><td>Short positions.</td></tr><tr><td>long_required_im</td><td>float</td><td>Initial margin change when buying one contract of an asset.</td></tr><tr><td>short_required_im</td><td>float</td><td>Initial margin change when selling one contract of an asset.</td></tr><tr><td>session</td><td>Session</td><td>Order session (Only applied to US stocks)</td></tr></table>

Example 

```python
from futu import *  
trdctx = OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host='127.0.0.1', pdret, data = trdctx.acctradinginfo_query(order_type=OrderType.NORMAL, code='HK.00')  
if ret == RET_OK:  
    print(data)  
    print(data['max_cash_and_margin_buy']) [0]) # Get maximum quantity that can be else:  
    print('acctradinginfo_query error: ', data)  
trdctx.close() # Close the current connection 
```

# ? Output

```txt
max_cash_buy max_cash_and_margin_buy max_position_buy max_buy_short max  
0 0.0 1500.0 0.0 0.0 1500.0 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

# Tips

The cash account does not support trading derivatives, so it is unsupported to query options through the cash account. 

# Get Positions

position_list_query(code='', position_market=TrdMarket.NONE, pl_ratio_min $\cdot$ None, pl_ratio_max $\cdot$ None, trd_env=TrdEnv.REAL, acc_id=0, acc_index ${ \tt = } 0$ , refresh_cache=False, asset_category=AssetCategory.NONE) 

. Description 

Query the holding position list of a specific trading account 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Security symbol.</td></tr><tr><td>position_market</td><td>TrdMarket</td><td>Filter positions by market.</td></tr><tr><td>pl_ratio_min</td><td>float</td><td>The lower limit of the current gain or loss ratio filter.</td></tr><tr><td>pl_ratio_max</td><td>float</td><td>The upper limit of the current gain or loss ratio filter.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>refresh_cache</td><td>bool</td><td>Whether to refresh the cache.</td></tr><tr><td>asset_category</td><td>AssetCategory</td><td>Asset category</td></tr></table>

Return 

Field 

Type 

Description 

<table><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, list of positions is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

List of positions format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>position_side</td><td>PositionSide</td><td>Position direction.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>position_market</td><td>TrdMarket</td><td>Position market.</td></tr><tr><td>qty</td><td>float</td><td>The number of holdings.</td></tr><tr><td>can_buy_qty</td><td>float</td><td>Available quantity.</td></tr><tr><td>currency</td><td>Currency</td><td>Transaction currency.</td></tr><tr><td>nominal_price</td><td>float</td><td>Market price.</td></tr><tr><td>cost_price</td><td>float</td><td>Diluted Cost (for securities account). Average Cost (for futures account).</td></tr><tr><td>cost_price_valid</td><td>bool</td><td>Whether the cost price is valid.</td></tr><tr><td>average_cost</td><td>float</td><td>Average cost price</td></tr><tr><td>diluted_cost</td><td>float</td><td>Diluted cost price</td></tr><tr><td>market_val</td><td>float</td><td>Market value.</td></tr><tr><td>pl_ratio</td><td>float</td><td>Proportion of gain or loss(under diluted cost price)</td></tr><tr><td>pl_ratio_valid</td><td>bool</td><td>Whether the gain or loss ratio is valid.</td></tr><tr><td>pl_ratio_avg_cost</td><td>float</td><td>Proportion of gain or loss(under average cost price)</td></tr><tr><td>pl_val</td><td>float</td><td>Gain or loss.</td></tr><tr><td>pl_val_valid</td><td>bool</td><td>Whether the gain or loss is valid.</td></tr><tr><td>today_pl_val</td><td>float</td><td>Gain or loss today.</td></tr><tr><td>today_trd_val</td><td>float</td><td>Transaction amount today.</td></tr><tr><td>today_buy_qty</td><td>float</td><td>Total volume purchased today.</td></tr><tr><td>today_buy_val</td><td>float</td><td>Total amount purchased today.</td></tr><tr><td>today_buy_qty</td><td>float</td><td>Total volume sold today.</td></tr><tr><td>today_buy_val</td><td>float</td><td>Total amount sold today.</td></tr><tr><td>unrealized_pl</td><td>float</td><td>Unrealized gain or loss.</td></tr><tr><td>realized_pl</td><td>float</td><td>Realized gain or loss.</td></tr><tr><td>position_id</td><td>int</td><td>Position ID</td></tr></table>

# ? Example

```python
from futu import *  
trdctx = OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host='127.0.0.1', pd  
ret, data = trdctx.position_list_query()  
if ret == RET_OK:  
    print(data)  
    if data.shape[0] > 0: # If the position list is not empty  
        print(data['stock_name'].0]) # Get the first stock name of the holding  
        print(data['stock_name'].values.tolist()) # Convert to list  
else: 
```

10 

11 

```python
print('position_list_query error: ', data)  
trdctx.close() # Close the current connection 
```

# . Output

1 

2 

3 

4 

```txt
code stock_name position_market qty can_sell_qty cost_price cost_price 0 HK.01810 XIAOMI-W HK 400.0 400.0 53.975 XIAOMI-W ['XIAOMI-W'] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

Call this interface, only when the cache is refreshed, will it be restricted by the frequency limit 

# Get Margin Data

get_margin_ratio(code_list) 

. Description 

Query the margin data of stocks. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code_list</td><td>list</td><td>Stock list.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, margin data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Margin data format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Stock code</td></tr><tr><td>is_long permit</td><td>bool</td><td>Is marginable trading allowed.</td></tr><tr><td>is_short Permit</td><td>bool</td><td>Is shortable trading allowed.</td></tr><tr><td>short_pool Remain</td><td>float</td><td>Short pool remaining.</td></tr><tr><td>short_fee_rate</td><td>float</td><td>Borrow rate.</td></tr><tr><td>alert_long_ratio</td><td>float</td><td>Marginable alert margin.</td></tr><tr><td>alert_short_ratio</td><td>float</td><td>Shortable alert margin.</td></tr><tr><td>im_long_ratio</td><td>float</td><td>Marginable initial margin.</td></tr><tr><td>im_short_ratio</td><td>float</td><td>Shortable initial margin.</td></tr><tr><td>mcm_long_ratio</td><td>float</td><td>Marginable margin call margin.</td></tr><tr><td>mcm_short_ratio</td><td>float</td><td>Shortable margin call margin.</td></tr><tr><td>mm_long_ratio</td><td>float</td><td>Marginable maintenance margin.</td></tr><tr><td>mm_short_ratio</td><td>float</td><td>Marginable maintenance margin.</td></tr></table>


Example


1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $\coloneqq$ '127.0.0.1'，p   
3 ret，data $=$ trdctx.get_margin_ratio(code_list $\coloneqq$ ['HK.00700','HK.09988'])   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 print(data['is_long Permit'] [0]) #Get whether marginable trading allowed f   
7 print(data['im_short_ratio'].values.tolist()) # Convert to list   
8 else:   
9 print('error:', data)   
10 trdctx.close() #After using the connection, remember to close it to prevent t 


. Output


```txt
1 code is_long permit is_short Permit short_pool Remain short_fee_rate 2 0 HK.00700 True True 1826900.0 0.89 3 1 HK.09988 True True 1150600.0 0.95 4 True   
5 [60.0, 50.0] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single user ID. 

For each request, the maximum number of stocks supported by the parameter is 100. 

Only HK stocks and US stocks are supported. 

# Get Account Cash Flow

get_acc_cash_flow(clearing_date='', trd_env=TrdEnv.REAL, acc_id=0, acc_index ${ \tt = } 0$ , cashflow_direction=CashFlowDirection.NONE) 

# Description

Query the cash flow list of a specified trading account on a specified date. This includes all transactions that affect cash balances, such as deposits/withdrawals, fund transfers, currency exchanges, buying/selling financial assets, margin interest, and securities lending interest. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>clearing_date</td><td>str</td><td>Clearing date.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>cashflowDirection</td><td>CashFlowDirection</td><td>Filter by the direction of cash flow (e.g., inflow/outflow).</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, account cash flow list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Account cash flow list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>cashflow_id</td><td>int</td><td>Cash flow ID</td></tr><tr><td>clearing_date</td><td>str</td><td>Clearing date.</td></tr><tr><td>settlement_date</td><td>str</td><td>Settlement date.</td></tr><tr><td>currency</td><td>Currency</td><td>Transaction currency.</td></tr><tr><td>cashflow_type</td><td>str</td><td>Cash flow type.</td></tr><tr><td>cashflowDirection</td><td>CashFlowDirection</td><td>Cash flow direction.</td></tr><tr><td>cashflow_amount</td><td>float</td><td>Cash flow amount (positive:inflow, negative:outflow).</td></tr><tr><td>cashflowRemark</td><td>str</td><td>Remarks.</td></tr></table>

# . Example

1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $= 127.0.0.1$ ,pc   
3 ret，data $=$ trdctx.get_acc_cash_flow(clearing_date $= 1$ 2025-02-18'，trd_env $\equiv$ TrdEnv   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 if data.shape[O] $>0$ ：#If account cash flow list is not empty   
7 print(data['cashflow_type'][O]) #Get direction of the first cash flow   
8 print(data['cashflow_amount'].values.tolist()) #Convert to list   
9 else:   
10 print('get_acc_cash_flow error:'，data)   
11 trdctx.close()   
12 

# . Output

```txt
1 cashflow_id clearing_date settlement_date currency cashflow_t2 0 16308 2025-02-27 2025-02-28 HKD Others 3 16357 2025-02-27 2025-03-03 HKD Others 4 2 16360 2025-02-27 2025-02-27 USD Fund Redempt 
```

3 16384 

2025-02-27 

2025-02-27 

HKD 

Fund Redemp 

Others 

[0.00, -104000.00, 23000.00, 104108.96] 

# Interface Limitations

A maximum of 20 requests per 30 seconds under a single account ID (acc_id). 

Cash flows are arranged in chronological order. 

Can not query cash flow list through paper trading accounts. 

# Place Orders

place_order(price, qty, code, trd_side, order_type=OrderType.NORMAL, adjust_limit $\cdot$ , trd_env=TrdEnv.REAL, acc_id $= 0$ , acc_index ${ \tt = } 0$ , remark $\cdot$ None, time_in_force=TimeInForce.DAY, fill_outside_rth $| =$ False, aux_price $=$ None, trail_type $=$ None, trail_value=None, trail_spread $=$ None, session $| =$ Session.NONE, jp_acc_type=SubAccType.JP_GENERAL, position_id=NONE) 

# . Description

Place order 

# Tips

The Python API is synchronous, but the network transport is asynchronous. When the receiving time interval is very short between the response packet of place_order and Order Fill Push Callback or Order Push Callback, it may happen that the response packet of place_order returns first, but the callback function is called first. For example: Order Push Callback may be called first, and then the place_order interface returns. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>price</td><td>float</td><td>Order price.</td></tr><tr><td>qty</td><td>float</td><td>Order quantity.</td></tr><tr><td>code</td><td>str</td><td>Code.</td></tr><tr><td>trdSide</td><td>TrdSide</td><td>Transaction direction.</td></tr><tr><td>order_type</td><td>OrderType</td><td>Order type.</td></tr><tr><td>adjust_limit</td><td>float</td><td>Price adjustment range.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>remark</td><td>str</td><td>Remark.</td></tr><tr><td>time_in_force</td><td>TimelnForce</td><td>Valid period.</td></tr><tr><td>fill_outside_rth</td><td>bool</td><td>Whether allow to execute the order during pre-market or after-hours market trades.</td></tr><tr><td>aux_price</td><td>float</td><td>Trigger price.</td></tr><tr><td>trail_type</td><td>TrailType</td><td>Trailing type.</td></tr><tr><td>trail_value</td><td>float</td><td>Trailing amount/ratio.</td></tr><tr><td>trail_spread</td><td>float</td><td>Specify spread.</td></tr><tr><td>session</td><td>Session</td><td>US stocks Trading Session</td></tr><tr><td>jp_acc_type</td><td>SubAccType</td><td>JP sub account type</td></tr><tr><td>position_id</td><td>int</td><td>Position ID</td></tr></table>

# ? Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, order list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Order list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trdSide</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>order_type</td><td>OrderType</td><td>Order type.</td></tr><tr><td>order_status</td><td>OrderStatus</td><td>Order status.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>qty</td><td>float</td><td>Order quantity.</td></tr><tr><td>price</td><td>float</td><td>Order price.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>updated_time</td><td>str</td><td>Last update time.</td></tr><tr><td>dealt_qty</td><td>float</td><td>Deal quantity</td></tr><tr><td>dealt_avg_price</td><td>float</td><td>Average deal price.</td></tr><tr><td>last_err_MSG</td><td>str</td><td>The last error description.</td></tr><tr><td>remark</td><td>str</td><td>Identification of remarks when placing an order.</td></tr><tr><td>time_in_force</td><td>TimeInForce</td><td>Valid period.</td></tr><tr><td>fill_outside_rth</td><td>bool</td><td>Whether pre-market and after-hours are needed.</td></tr><tr><td>session</td><td>Session</td><td>Order session (Only applied to US stocks)</td></tr><tr><td>aux_price</td><td>float</td><td>Traget price.</td></tr><tr><td>trail_type</td><td>TrailType</td><td>Trailing type.</td></tr><tr><td>trail_value</td><td>float</td><td>Trailing amount/ratio.</td></tr><tr><td>trail_spread</td><td>float</td><td>Specify spread.</td></tr></table>

# Example

1 from futu import \*   
2 pwd_unlock $=$ '123456'   
3 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $= 127.0.0.1$ ,pc   
4 ret,data $=$ trdctx.unlock_trade(pwd_unlock） # If you use a live trading account   
5 if ret $= =$ RET_OK:   
6 ret,data $=$ trdctx.place_order(price $= 510.0$ ,qty $= 100$ ,code $= "HK.00700"$ ,trd_s   
7 if ret $= =$ RET_OK:   
8 print(data)   
9 print(data['order_id'][0]) #Get the order ID of the placed order   
10 print(data['order_id'].values.tolist()) # Convert to list   
11 else:   
12 print('place_order error:'，data)   
13 else:   
14 print('unlock_trade failed:'，data)   
15 trdctx.close() 

# ? Output

```txt
1 code stock_name trd_side order_type order_status order_id qty   
2 0 HK.00700 Tencent BUY NORMAL SUBMITTING 38196006548709500 10   
3 38196006548709500   
4 [38196006548709500'] 
```

# Interface Limitations

A maximum of 15 requests per 30 seconds under a single account ID (acc_id), and the interval between two consecutive requests cannot be less than 0.02 seconds. 

When using live trading accounts, you need to unlock trade before calling Place Order interface, but when using paper trading accounts, you do not need to unlock trade. 

# Tips

Required parameters for each order type: Click here to learn more. 

Each broker sets limits on shares or amounts for single orders of various trading products. Exceeding these limits may result in order failures: Click here to learn more. 

Locking position is not supported for shortable securities, that means you can not hold a long position and a short position at the same time. 

If you want to close out position of a shortable securities, you need to get the direction of the position and send an opposite order with the same quantity. 

If you want to reversing trade of a shortable securities, there are 2 steps: 1. you need to get the direction of the position and send an opposite order with the same quantity. 2. Send an opposite order again to open the reverse trade. For example: If you want to reverse trade of 1 long position of HK.HSI2012, you need to close the long position first and then sell short the contract. 

Only limit orders can be allowed during US stocks 24 Hour Trading Hour. You can choose Day, Good-Till-Cancelled (GTC) as the time-in-force. 24-hour order runs from Sunday 8:00 PM to Friday 8:00 PM ET, covering regular trading hours plus premarket, post-market, and overnight trading sessions. You can place orders anytime during this period. 

Paper trading of US stocks does not support irregular trading hours (including pre/post-market and overnight). 

# Modify or Cancel Orders

modify_order(modify_order_op, order_id, qty, price, adjust_limit=0, trd_env=TrdEnv.REAL, acc_id=0, acc_index $\cdot ^ { \circ }$ , aux_price=None, trail_type=None, trail_value=None, trail_spread=None) 

# . Description

Modify the price and quantity of orders, cancel orders, delete orders, enable or disable orders, etc. 

For HKCC market, it is invalid to change orders, except that cancelling orders is supported. 

# ? Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>modify_order_op</td><td>ModifyOrderOp</td><td>Modify order operation type.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>qty</td><td>float</td><td>The quantity after the order is changed.</td></tr><tr><td>price</td><td>float</td><td>The price after the order is changed.</td></tr><tr><td>adjust_limit</td><td>float</td><td>Price adjustment range.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>aux_price</td><td>float</td><td>Trigger price.</td></tr><tr><td>trail_type</td><td>TrailType</td><td>Trailing type.</td></tr><tr><td>trail_value</td><td>float</td><td>Trailing amount/ratio.</td></tr><tr><td>trail_spread</td><td>float</td><td>Specify spread.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, modification information is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Modification information format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr></table>

Example 

1 from futu import \*   
2 pwd_unlock $=$ '123456'   
3 trdctx $=$ OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host $=$ 127.0.0.1', p   
4 ret, data $=$ trdctx.unlock_trade(pwd_unlock) # If you use a live trading account   
5 if ret $= =$ RET_OK:   
6 order_id $=$ "8851102695472794941"   
7 ret, data $=$ trdctxmodify_order(ModifyOrderOp.CANCEL, order_id, 0, 0)   
8 if ret $= =$ RET_OK:   
9 print(data)   
10 print(data['order_id'] [0]) # Get the order ID of the modified order   
11 print(data['order_id'].values.tolist()) # Convert to list   
12 else:   
13 print('modify_order error: ', data)   
14 else:   
15 print('unlock_trade failed: ', data)   
16 trd_ctx.close() 

# . Output

```txt
1 trd_env order_id   
2 REAL 8851102695472794941   
3 8851102695472794941   
4 ['8851102695472794941'] 
```

```python
cancel_all_order(trd_env=TrdEnv.REAL, acc_id=0, acc_index=0, trdmarket=TrdMarket.NONE) 
```

# ? Description

Cancel all orders. Paper trading and HKCC trading accounts do not support all cancellations. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>trdmarket</td><td>TrdMarket</td><td>Transaction market selection.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>int</td><td>Returned value. On success, ret == RET_OK. On error, ret != RET_OK.</td></tr><tr><td rowspan="2">data</td><td rowspan="2">str</td><td>If ret == RET_OK, modification information is returned.</td></tr><tr><td>If ret != RET_OK, error description is returned.</td></tr></table>

Modification information format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment</td></tr><tr><td>order_id</td><td>str</td><td>Order number</td></tr></table>

# Example

1 from futu import \*   
2 pwd_unlock $=$ '123456'   
3 trdctx $=$ OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host $=$ 127.0.0.1', p   
4 ret,data $=$ trdctx.unlock_trade(pwd_unlock） # If you use a live trading account   
5 if ret $= =$ RET_OK:   
6 ret,data $=$ trdctx.cancel_all_order()   
7 if ret $= =$ RET_OK:   
8 print(data)   
9 else:   
10 print('cancel_all_order error:'，data)   
11 else:   
12 print('unlock_trade failed:'，data)   
13 trdctx.close() 

# . Output

```txt
1 success 
```

# Interface Limitations

A maximum of 20 requests per 30 seconds under a single account ID (acc_id), and the time interval between two consecutive requests should not be less than 0.04 seconds. 

When using live trading accounts, you need to unlock trade before calling Modify or Cancel Orders interface, but when using paper trading accounts, you do not need to unlock trade. 

Tip 

For the execution of modify the order, to learn more about the required parameters for each order type, please click here. 

If you want to modify the quantity of the order, the parameter qty should be equal to the total quantity of the expected filled. 

For example: 

The quantity of an order is N shares, with n shares filled. For the unfilled (N-n) shares, if you want to cancel $X$ shares, the parameter modify_order_op should be NORMAL, qty should be (N-x). 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/30699b5a6c6eb8b7a6e27cdf172fffef66ffe6fec25b28db66c2755bae140ab3.jpg)


If you want to cancel an order, the parameter modify_order_op should be CANCEL. For example: 

The quantity of an order is $N$ shares, with n shares filled. If you want to cancel the unfilled (N-n) shares, modify_order_op should be CANCEL, and qty and price will be ignored. 

# Get open Orders

order_list_query(order_id="", order_market=TrdMarket.NONE, status_filter_list $\Finv$ , code='', start='' end='', trd_env=TrdEnv.REAL, acc_id=0, acc_index $\boldsymbol { \cdot }$ , refresh_cache $^ { 1 } =$ False) 

. Description 

Query the open order list of the specified trading account 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>order_id</td><td>str</td><td>Order id.</td></tr><tr><td>order_market</td><td>TrdMarket</td><td>Filter orders by security market.</td></tr><tr><td>status_filter_list</td><td>list</td><td>Order status filter conditions.</td></tr><tr><td>code</td><td>str</td><td>Security symbol.</td></tr><tr><td>start</td><td>str</td><td>Start time.</td></tr><tr><td>end</td><td>str</td><td>End time.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>refresh_cache</td><td>bool</td><td>Whether to refresh the cache.</td></tr></table>

Return 

Field 

Type 

Description 

<table><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, order list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Order list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trdSide</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>order_type</td><td>OrderType</td><td>Order type.</td></tr><tr><td>order_status</td><td>OrderStatus</td><td>Order status.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>order_market</td><td>TrdMarket</td><td>Order market.</td></tr><tr><td>qty</td><td>float</td><td>Order quantity.</td></tr><tr><td>price</td><td>float</td><td>Order price.</td></tr><tr><td>currency</td><td>Currency</td><td>Transaction currency.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>updated_time</td><td>str</td><td>Last update time.</td></tr><tr><td>dealt_qty</td><td>float</td><td>Deal quantity</td></tr><tr><td>dealt_avg_price</td><td>float</td><td>Average deal price.</td></tr><tr><td>last_err_MSG</td><td>str</td><td>The last error description.</td></tr><tr><td>remark</td><td>str</td><td>Identification of remarks when placing an order.</td></tr><tr><td>time_in_force</td><td>TimeInForce</td><td>Valid period.</td></tr><tr><td>fill_outside_rth</td><td>bool</td><td>Whether pre-market and after-hours are needed.</td></tr><tr><td>session</td><td>Session</td><td>Order session (Only applied to US stocks)</td></tr><tr><td>aux_price</td><td>float</td><td>Traget price.</td></tr><tr><td>trail_type</td><td>TrailType</td><td>Trailing type.</td></tr><tr><td>trail_value</td><td>float</td><td>Trailing amount/ratio.</td></tr><tr><td>trail_spread</td><td>float</td><td>Specify spread.</td></tr><tr><td>jp_acc_type</td><td>SubAccType</td><td>JP sub account type</td></tr></table>


. Example


1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $= 127.0.0.1$ ,p   
3 ret，data $=$ trdctx.order_list_query()   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 if data.shape[0] $>0$ ：#If the order list is not empty   
7 print(data['order_id'] [0]) #Get the first order ID of the order list to   
8 print(data['order_id'].values.tolist()) #Convert to list   
9 else:   
10 print('order_list_query error:'，data)   
11 trdctx.close() 


. Output


```txt
1 code stock_name order_market trd_side order_type order_st 2 0 HK.00700 HK BUY NORMAL CANCELLED_ALL 
```

3 6644468615272262086 

4 '6644468615272262086 

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

It will be restricted by the frequency limit for this interface only when the cache is refreshed 

# Tips

Open orders are arranged in chronological order: earlier orders return first, followed by later orders. 

# Get Historical Orders

history_order_list_query(status_filter_list=[], code='' order_market=TrdMarket.NONE, start='' end='' trd_env=TrdEnv.REAL, acc_id=0, acc_index $\boldsymbol { \cdot }$ ) 

. Description 

Query the historical order list of a specified trading account 

. Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>status_filter_list</td><td>list</td><td>Order status filter conditions.</td></tr><tr><td>code</td><td>str</td><td>Security symbol.</td></tr><tr><td>order_market</td><td>TrdMarket</td><td>Filter orders by security market.</td></tr><tr><td>start</td><td>str</td><td>Start time.</td></tr><tr><td>end</td><td>str</td><td>End time.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr></table>

The combination of start and end is as follows 

<table><tr><td>Start type</td><td>End type</td><td>Description</td></tr><tr><td>str</td><td>str</td><td>start and end are the specified dates respectively.</td></tr><tr><td>None</td><td>str</td><td>start is 90 days before end.</td></tr><tr><td>str</td><td>None</td><td>end is 90 days after start.</td></tr><tr><td>None</td><td>None</td><td>start is 90 days before, end is the current date.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, order list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Order list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trdSide</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>order_type</td><td>OrderType</td><td>Order type.</td></tr><tr><td>order_status</td><td>OrderStatus</td><td>Order status.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>order_market</td><td>TrdMarket</td><td>Order market.</td></tr><tr><td>qty</td><td>float</td><td>Order quantity.</td></tr><tr><td>price</td><td>float</td><td>Order price.</td></tr><tr><td>currency</td><td>Currency</td><td>Transaction currency.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>updated_time</td><td>str</td><td>Last update time.</td></tr><tr><td>dealt_qty</td><td>float</td><td>Deal quantity</td></tr><tr><td>dealt_avg_price</td><td>float</td><td>Average deal price.</td></tr><tr><td>last_err msg</td><td>str</td><td>The last error description.</td></tr><tr><td>remark</td><td>str</td><td>Identification of remarks when placing an order.</td></tr><tr><td>time_in_force</td><td>TimelnForce</td><td>Valid period.</td></tr><tr><td>fill_outside_rth</td><td>bool</td><td>Whether pre-market and after-hours are needed.</td></tr><tr><td>session</td><td>Session</td><td>Order session (Only applied to US stocks)</td></tr><tr><td>aux_price</td><td>float</td><td>Traget price.</td></tr><tr><td>trail_type</td><td>TrailType</td><td>Trailing type.</td></tr><tr><td>trail_value</td><td>float</td><td>Trailing amount/ratio.</td></tr><tr><td>trail_spread</td><td>float</td><td>Specify spread.</td></tr><tr><td>jp_acc_type</td><td>SubAccType</td><td>JP sub account type</td></tr></table>

# Example

1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $= 127.0.0.1$ ,pc   
3 ret，data $=$ trdctx-history_order_list_query()   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 if data.shape[0] $>0$ ：#If the order list is not empty   
7 print(data['order_id'] [0]) #Get Order ID of the first holding position 

```python
8 print(data['order_id'].values.tolist()) # Convert to list   
9 else:   
10 print('history_order_list_query error: ', data)   
11 trdctx.close() 
```


Output


```txt
1 code stock_name order_market trd_side order_type order_sta   
2 0 HK.00700 HK BUY NORMAL CANCELLED_ALL 664   
3 6644468615272262086   
4 ['6644468615272262086'] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

# Tips

Historical orders are arranged in reverse chronological order: later orders return first, followed by earlier orders. 

# Orders Push Callback

on_recv_rsp(self, rsp_pb) 

# Description

In response to orders push, asynchronously process the order status information pushed by OpenD. After receiving the order status information pushed by OpenD, this function is called.. You need to override on_recv_rsp in the derived class. 

# . Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Trd_UpdateOrder_pb2.Response</td><td>This parameter does not need to be processed in the derived class.</td></tr></table>

# Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, order list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

# Order list format as follows:

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trdSide</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>order_type</td><td>OrderType</td><td>Order type.</td></tr><tr><td>order_status</td><td>OrderStatus</td><td>Order status.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>qty</td><td>float</td><td>Order quantity.</td></tr><tr><td>price</td><td>float</td><td>Order price.</td></tr><tr><td>currency</td><td>Currency</td><td>Transaction currency.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>updated_time</td><td>str</td><td>Last update time.</td></tr><tr><td>dealt_qty</td><td>float</td><td>Deal quantity</td></tr><tr><td>dealt_avg_price</td><td>float</td><td>Average deal price.</td></tr><tr><td>last_err_MSG</td><td>str</td><td>The last error description.</td></tr><tr><td>remark</td><td>str</td><td>Identification of remarks when placing an order.</td></tr><tr><td>time_in_force</td><td>TimelnForce</td><td>Valid period.</td></tr><tr><td>fill_outside_rth</td><td>bool</td><td>Whether pre-market and after-hours are needed.</td></tr><tr><td>session</td><td>Session</td><td>Order session (Only applied to US stocks)</td></tr><tr><td>aux_price</td><td>float</td><td>Traget price.</td></tr><tr><td>trail_type</td><td>TrailType</td><td>Trailing type.</td></tr><tr><td>trail_value</td><td>float</td><td>Trailing amount/ratio.</td></tr><tr><td>trail_spread</td><td>float</td><td>Specify spread.</td></tr></table>


. Example


1 from futu import \*   
2 from time import sleep   
3 class TradeOrderTest(TradeOrderHandlerBase):   
4 ""order update push""   
5 def on_recv_rsp(self, rsp_cb):   
6 ret, content $=$ super(TradeOrderTest,self).on_recv_rsp(rsp_cb)   
7 if ret $= =$ RET_OK:   
8 print("TradeOrderTest content $\equiv$ {}\\n".format(content))   
9 return ret, content   
10 trdctx $=$ OpenSecTradeContext过滤器_trdmarket $\equiv$ TrdMarket.HK，host $= 127.0.0.1$ ，p   
11 trdctx.sethandler(TradeOrderTest())   
12 print(trdctx.place_order(price $= 518.0$ ,qty $= 100$ ，code $= "HK.00700"$ ，trdSide $\equiv$ TrdSide   
13   
14 sleep(15)   
15 trdctx.close()


Output


```txt
1 \*TradeOrderTest content= trd_env code stock_name dealt_avg_price dealt_2 0 REAL HK.00700 Tencent 0.0 0.0 100.0 72625263708 
```

# Get Order Fee

order_fee_query(order_id_list=[], acc_id=0, acc_index=0, trd_env=TrdEnv.REAL) 

# . 介绍

Get specified orders' fee details. (Minimum version requirement: 8.2.4218) 

# . 参数

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>order_id_list</td><td>list</td><td>Order id list.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr></table>

# . 返回

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, order fee list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Order list format as follows： 

<table><tr><td>字段</td><td>类型</td><td>说明</td></tr><tr><td>order_id</td><td>str</td><td>Order ID</td></tr><tr><td>fee_amount</td><td>float</td><td>Total fee of the order.</td></tr><tr><td>fee_details</td><td>list</td><td>Fee details of the order.</td></tr></table>


Example


1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.US, host $= 127.0.0.1$ ,pc   
3 ret1,data1 $=$ trdctx-history_order_list_query(status_filter_list $=$ [OrderStatus.F]   
4 if ret1 $= =$ RET_OK:   
5 if data1.shape[0] $>0$ # If the order list is not empty   
6 ret2,data2 $=$ trdctx.order_fee_query(data1['order_id'].values.tolist())   
7 if ret2 $= =$ RET_OK:   
8 print(data2)   
9 print(data2['fee_details'][0]) # Get fee details of the first order   
10 else:   
11 print('order_fee_query error:'，data2)   
12 else:   
13 print('order_list_query error:'，data1)   
14 trdctx.close() 


Output


```txt
order_id fee_amount 1   
2 v3_20240314_12345678_MTc4NzA5NzY50TA30DAzMzMwn 10.46 [(Commission,5.85)   
3 1 v3_20240318_12345678_MTM5Nzc5MDYxNDY1NDM1MDI1M 2.25 [(Commission,0.99)   
4 [('Commission',5.85)，('Platform Fee'，2.7)，('ORF'，0.11)，('OCC Fee'，0.18)， 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

Only orders after 2018-01-01 are supported. 

Can not query order fee through paper trading accounts. 

Can not query order fee through Moomoo CA accounts. 

# Subscribe to Transaction Push

Python does not need to subscribe to transaction push 

# Get Today's Deals

deal_list_query(code="", deal_market= TrdMarket.NONE, trd_env=TrdEnv.REAL, acc_id=0, acc_index ${ \tt = } 0$ , refresh_cache $=$ False) 

Description 

Query today's deal list of a specific trading account. 

This feature is only available for live trading and not for paper trading. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Security symbol.</td></tr><tr><td>deal_market</td><td>TrdMarket</td><td>Filter deals by security market.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr><tr><td>refresh_cache</td><td>bool</td><td>Whether to refresh the cache.</td></tr></table>

? Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, transaction list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Transaction list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trd_side</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>deal_id</td><td>str</td><td>Deal number.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>deal_market</td><td>TrdMarket</td><td>Deal market.</td></tr><tr><td>qty</td><td>float</td><td>Quantity of shares bought/sold on this fill.</td></tr><tr><td>price</td><td>float</td><td>Fill price.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>counter_broker_id</td><td>int</td><td>Counter broker ID.</td></tr><tr><td>counter_broker_name</td><td>str</td><td>Counter broker name.</td></tr><tr><td>status</td><td>DealStatus</td><td>Deal status.</td></tr><tr><td>jp_acc_type</td><td>SubAccType</td><td>JP sub account type</td></tr></table>

# . Example

```python
from futu import *  
trdCtx = OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host='127.0.0.1', pd  
ret, data = trdCtxDeal_list_query()  
if ret == RET_OK:  
    print(data)  
    if data.shape[0] > 0: # If the order fill list is not empty  
        print(data['order_id']) [0] # Get the first order ID of the transaction  
        print(data['order_id'].values.tolist()) # Convert to list  
else: 
```

10 

11 

print('deal_list_query error: data) 

trd_ctx.close() 

# Output

1 

2 

3 

4 

code stock_name 

0 HK.00388 

Hong Kong Exchanges and Clearing 

915 

['4665291631090960915'] 

deal_market 

HK 

deal_id 

5056208452274069375 466 

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

It will be restricted by the frequency limit for this interface only when refresh_cache is True 

# Tips

Today's deals are arranged in chronological order: earlier deals return first, followed by later deals. 

# Get Historical Deals

history_deal_list_query(code='', deal_market=TrdMarket.NONE, start= end= trd_env=TrdEnv.REAL, acc_id=0, acc_index $\boldsymbol { \cdot }$ ) 

# Description

Query historical deal list of a specific trading account. 

This feature is only available for live trading and not for paper trading. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>code</td><td>str</td><td>Security symbol.</td></tr><tr><td>deal_market</td><td>TrdMarket</td><td>Filter deals by security market.</td></tr><tr><td>start</td><td>str</td><td>Start time.</td></tr><tr><td>end</td><td>str</td><td>End time.</td></tr><tr><td>trd_env</td><td>TrdEnv</td><td>Trading environment.</td></tr><tr><td>acc_id</td><td>int</td><td>Trading account ID.</td></tr><tr><td>acc_index</td><td>int</td><td>The account number in the trading account list.</td></tr></table>

The combination of start and end is as follows 

<table><tr><td>Start type</td><td>End type</td><td>Description</td></tr><tr><td>str</td><td>str</td><td>start and end are the specified dates respectively.</td></tr><tr><td>None</td><td>str</td><td>start is 90 days before end.</td></tr><tr><td>str</td><td>None</td><td>end is 90 days after start.</td></tr><tr><td>None</td><td>None</td><td>start is 90 days before, end is the current date.</td></tr></table>

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, transaction list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Transaction list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trd_side</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>deal_id</td><td>str</td><td>Deal number.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>deal_market</td><td>TrdMarket</td><td>Deal market.</td></tr><tr><td>qty</td><td>float</td><td>Quantity of shares bought/sold on this fill.</td></tr><tr><td>price</td><td>float</td><td>Fill price.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>counter_broker_id</td><td>int</td><td>Counter broker ID.</td></tr><tr><td>counter_broker_name</td><td>str</td><td>Counter broker name.</td></tr><tr><td>status</td><td>DealStatus</td><td>Deal status.</td></tr><tr><td>jp_acc_type</td><td>SubAccType</td><td>JP sub account type</td></tr></table>

# Example

1 from futu import \*   
2 trdctx $=$ OpenSecTradeContext.filter_trdmarket $\equiv$ TrdMarket.HK, host $\coloneqq$ '127.0.0.1'，p   
3 ret，data $=$ trdctx-historyDeal_list_query()   
4 if ret $= =$ RET_OK:   
5 print(data)   
6 if data.shape[0] $>0$ ：#If the order fill list is not empty   
7 print(data['deal_id'] [0]) #Get the first deal ID of the history order   
8 print(data['deal_id'].values.tolist()) #Convert to list   
9 else:   
10 print('historyDeal_list_query error:'，data)   
11 trdctx.close(） #Close the current connection 

# . Output

```txt
1 code stock_name deal_market deal_id 2 0 HK.00388 Hong Kong Exchanges and Clearing HK 5056208452274069375 3 5056208452274069375 4 ['5056208452274069375'] 
```

# Interface Limitations

A maximum of 10 requests per 30 seconds under a single account ID (acc_id). 

# Tips

Historical deals are arranged in reverse chronological order: later deals return first, followed by earlier deals. 

# Deals Push Callback

on_recv_rsp(self, rsp_pb) 

# Description

In response to the transaction push, asynchronously process the transaction status information pushed by OpenD. After receiving the order fill information pushed by OpenD, this function is called. You need to override on_recv_rsp in the derived class. This feature is only available for live trading and not for paper trading. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>rsp_pb</td><td>Trd_UpdateOrderFill_pb2.Response</td><td>This parameter does not need to be processed in the derived class.</td></tr></table>

# ? Return

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>RET_CODE</td><td>Interface result.</td></tr><tr><td rowspan="2">data</td><td>pd.DataFrame</td><td>If ret == RET_OK, transaction list is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

Transaction list format as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>trd_side</td><td>TrdSide</td><td>Trading direction.</td></tr><tr><td>deal_id</td><td>str</td><td>Deal number.</td></tr><tr><td>order_id</td><td>str</td><td>Order ID.</td></tr><tr><td>code</td><td>str</td><td>Security code.</td></tr><tr><td>stock_name</td><td>str</td><td>Security name.</td></tr><tr><td>qty</td><td>float</td><td>Quantity of shares bought/sold on this fill.</td></tr><tr><td>price</td><td>float</td><td>Fill price.</td></tr><tr><td>create_time</td><td>str</td><td>Create time.</td></tr><tr><td>counter_broker_id</td><td>int</td><td>Counter broker ID.</td></tr><tr><td>counter_broker_name</td><td>str</td><td>Counter broker name.</td></tr><tr><td>status</td><td>DealStatus</td><td>Deal status.</td></tr></table>


. Example


1 from futu import \*   
2 from time import sleep   
3 class TradeDealTest(TradeDealHandlerBase):   
4 ""order update push""   
5 def on_recv_rsp(self, rsp_cb):   
6 ret, content $=$ super(TradeDealTest,self).on_recv_rsp(rsp_cb)   
7 if ret $= =$ RET_OK:   
8 print("TradeDealTest content $\equiv$ {}".format(content))   
9 return ret, content   
10   
11 trdctx $=$ OpenSecTradeContext滤器_trdmarket $\equiv$ TrdMarket.HK，host $= 127.0.0.1$ ，p   
12 trdctx.sethandler(TradeDealTest())   
13 print(trdctx.place_order(price $= 595.0$ ,qty $= 100$ ，code $= 1$ "HK.00700"，trdSide $\equiv$ TrdSide   
14   
15 sleep(15)   
16 trdctx.close()


. Output


```txt
TradeDealTest content= trd_env code stock_name deal_id 0 REAL HK.00700 Tencent 2511067564122483295 8561504228375901919 100 
```

# Trading Definitions

# Account Risk Control Level

CltRiskLevel 

. NONE 

Unknown 

. SAFE 

Safe 

WARNING 

Warning 

. DANGER 

Danger 

ABSOLUTE_SAFE 

Absolutely safe 

. OPT_DANGER 

Danger 

# Tips

It is recommanded to use risk_status field to get risk status of futures account, see CltRiskStatus 

# Currency Type

Currency 

. NONE 

Unknown currency 

. HKD 

HK dollar 

. USD 

US dollar 

. CNH 

Offshore RMB 

. JPY 

Japanese Yen 

. SGD 

SG dollar 

AUD 

Australian dollar 

. CAD 

Canadian dollar 

. MYR 

Malaysian Ringgit 

# TrailType

TrailType 

. NONE 

Unknown 

RATIO 

Trailing ratio 

AMOUNT 

Trailing amount 

# Modify Order Operation

ModifyOrderOp 

. NONE 

Unknown operation 

. NORMAL 

Modify order 

. CANCEL 

Cancel 

. DISABLE 

Disable 

ENABLE 

Enable 

DELETE 

Delete 

# Transaction Status

DealStatus 

. OK 

Transaction success 

. CANCELLED 

Transaction cancelled 

. CHANGED 

Transaction changed 

# Order Status

OrderStatus 

. NONE 

Unknown status 

WAITING_SUBMIT 

Queued 

. SUBMITTING 

Submitting 

SUBMITTED 

Working 

FILLED_PART 

Partially filled 

FILLED_ALL 

Fully filled 

CANCELLED_PART 

Partially cancelled 

. CANCELLED_ALL 

Fully cancelled 

FAILED 

Failed. Rejected by server. 

. DISABLED 

Deactivated 

. DELETED 

Deleted, only unfilled orders can be deleted 

# Order Type

# Tips

Order types supported in live trading. 

Paper trade only supports limit orders (NORMAL) and market orders (MARKET). 

# OrderType

. NONE 

Unknown type. 

? NORMAL 

Limit orders. 

. MARKET 

Market orders. 

ABSOLUTE_LIMIT 

Absolute limit orders. 

? AUCTION 

At-auction market orders. 

AUCTION_LIMIT 

At-auction limit orders. 

. SPECIAL_LIMIT 

Special limit orders. 

. SPECIAL_LIMIT_ALL 

AON special limit orders. 

STOP 

Stop orders. 

? STOP_LIMIT 

Stop Limit orders. 

. MARKET_IF_TOUCHED 

Market if Touched orders. 

. LIMIT_IF_TOUCHED 

Limit if Touched orders. 

. TRAILING_STOP 

Trailing Stop orders. 

TRAILING_STOP_LIMIT 

Trailing Stop Limit orders. 

TWAP_LIMIT 

Time Weighted Average Price Limit orders (HK and US securities only). 

TWAP 

Time Weighted Average Price Market orders (US securities only). 

. VWAP_LIMIT 

Volume Weighted Average Price Limit orders (HK and US securities only). 

VWAP 

Volume Weighted Average Price Market orders (US securities only). 

# Position Direction

PositionSide 

NONE 

Unknown position 

. LONG 

Long position, by default 

. SHORT 

Short position 

# Account Type

TrdAccType 

NONE 

Unknown type 

CASH 

Cash account 

. MARGIN 

Margin account 

TFSA 

Canadian TFSA account 

RRSP 

Canadian RRSP account 

SRRSP 

Canadian SRRSP account 

. DERIVATIVE 

Japanese derivative account 

# Trading Environment

TrdEnv 

. SIMULATE 

Simulated environment 

REAL 

Real environment 

# Transaction Market

TrdMarket 

. NONE 

Unknown market 

HK 

Hong Kong market 

. US 

US market 

. CN 

A-share market 

. HKCC 

HKCC market 

. FUTURES 

Futures market 

FUTURES_SIMULATE_US 

US futures simulated market 

FUTURES_SIMULATE_HK 

Hong Kong futures simulated market 

. FUTURES_SIMULATE_SG 

Singapore futures simulated market 

FUTURES_SIMULATE_JP 

Japan futures simulated market 

HKFUND 

HK fund market 

. USFUND 

US fund market 

SG 

SG market 

. JP 

JP market 

. AU 

AU market 

. MY 

MY market 

. CA 

CA market 

# Account Status

TrdAccStatus 

. ACTIVE 

Active account 

. DISABLED 

Disabled account 

# Account Structure

TrdAccRole 

NONE 

Unknown 

MASTER 

Master account 

NORMAL 

Normal account 

. IPO 

Malaysian IPO account 

# Transaction Securities Market

# Transaction Direction

TrdSide 

? NONE 

Unknown direction 

. BUY 

Buy 

. SELL 

Sell 

SELL_SHORT 

Sell short 

. BUY_BACK 

Buy back 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/bfa5c71dad15e9ff1eae7851029a4d47111c6c13a0bbf2d670b1371edab5e0a1.jpg)


# Tips

It is recommanded that only use Buy or Sell as the input parameter of direction of place_order interface. 

BuyBack and SellShort is only used as the display field for Get Order List , Get History Order List, Orders Push Callback, Get Today's Deals, Get Historical Deals and Deals Push Callback interface. 

# Order Validity Period

TimeInForce 

. DAY 

Good for the day 

. GTC 

Good until cancel 

# Securities Firm to Which the Account Belongs

SecurityFirm 

. NONE 

Unknown 

FUTUSECURITIES 

FUTU HK 

FUTUINC 

Moomoo US 

. FUTUSG 

Moomoo SG 

FUTUAU 

Moomoo AU 

FUTUCA 

Moomoo CA 

FUTUMY 

Moomoo MY 

FUTUJP 

# Simulate Account Type

SimAccType 

. NONE 

Unknown 

. STOCK 

Stock simulation account 

. OPTION 

Option simulation account 

. FUTURES 

Futures simulation account 

# Account Risk Control Status

CltRiskStatus 

. NONE 

Unknown 

LEVEL1 

Very Safe 

LEVEL2 

Safe 

LEVEL3 

Safe 

. LEVEL4 

Low Risk 

. LEVEL5 

Medium Risk 

. LEVEL6 

High Risk 

. LEVEL7 

Warning 

LEVEL8 

Margin Call 

. LEVEL9 

Margin Call 

# Day-trading Status

DtStatus 

NONE 

Unknown 

. Unlimited 

Unlimited 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/b4487280aa2e402517cddee09f45ac03f9947b4286b86fcf4a461183550e73bf.jpg)


EM_Call 

EM-Call 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/2feb5bb7139a9f132e767d615e74cdb27e74363762abcc06d756df0e806a16f3.jpg)


DT_Call 

DT-Call 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/1b5525f3e6e828c064274c14fd6966e23edc3896c768a6211160325057bdf445.jpg)


# Cash Flow Direction

CashFlowDirection 

NONE 

Unknown 

. IN 

Cash Inflow 

. OUT 

Cash Outflow 

# JP Sub Account Type

SubAccType 

NONE 

Unknown 

JP_GENERAL 

General - long 

? JP_TOKUTEI 

Specified - long 

. JP_NISA_GENERAL 

General NISA 

JP_NISA_TSUMITATE 

Tsumitate NISA 

. JP_GENERAL_SHORT 

General - short 

. JP_TOKUTEI_SHORT 

Specified - short 

. JP_HONPO_GENERAL 

Domestic Margin Trading Collateral - General 

. JP_GAIKOKU_GENERAL 

Foreign Margin Trading Collateral - General 

JP_HONPO_TOKUTEI 

Domestic Margin Trading Collateral - Specified 

. JP_GAIKOKU_TOKUTEI 

Foreign Margin Trading Collateral - Specified 

JP_DERIVATIVE_LONG 

Derivatives Sub-account - Long 

. JP_DERIVATIVE_SHORT 

Derivatives Sub-account - Short 

. JP_HONPO_DERIVATIVE_GENERAL 

Domestic Derivatives Margin Sub-account - General 

. JP_GAIKOKU_DERIVATIVE_GENERAL 

Foreign Derivatives Margin Sub-account - General 

. JP_HONPO_DERIVATIVE_TOKUTEI 

Domestic Derivatives Margin Sub-account - Specific 

JP_GAIKOKU_DERIVATIVE_TOKUTEI 

# Asset Category

AssetCategory 

. NONE 

Unknown 

. JP 

Domestic 

. US 

Foreign 

# Transaction Category

# TrdCategory

```txt
1 enum TrdCategory
2 {
3     TrdCategory_Unknown = 0; //Unknown
4     TrdCategory_Security = 1; //Securities
5     TrdCategory_Future = 2; //Futures
6 } 
```

# Account Cash Information

# AccCashInfo

1 message AccCashInfo   
2 {   
3 optional int32 currency $= 1$ //Currency type, refer to Currency   
4 optional double cash $= 2$ //Cash balance   
5 optional double availableBalance $= 3$ //Available cash withdrawal amount 

```txt
6 7 
```

optional double netCashPower = 4; // Net cash power 

# Account Assets Information by Market


AccMarketInfo


1 message AccCashInfo   
2 {   
3 optional int32 trdMarket $= 1$ // Trading market, refer to TrdMarket   
4 optional double assets $= 2$ // Account assets information by market   
5 } 

# Transaction Protocol Public Header


TrdHeader


1 message TrdHeader   
2 {   
3 required int32 trdEnv $= 1$ ; //Trading environment, refer to the enumeration def   
4 required uint64 accID $= 2$ ; //Trading account, trading account should match to   
5 required int32 trdMarket $= 3$ ; //Trading market, refer to the enumeration def   
6 optional int32 jpAccType $= 4$ ; //JP sub account type, refer to TrdSubAccType   
7 } 

# Trading Account


TrdAcc


1 message TrdAcc   
2 {   
3 required int32 trdEnv $=$ 1; //Trading environment, refer to the enumeration def   
4 required uint64 accID $=$ 2; //Trading account   
5 repeated int32 trdMarketAuthList $=$ 3; //The trading market permissions support 

```c
optional int32 accType = 4; //Account type, refer to TrdAccType  
optional string cardNum = 5; //card number  
optional int32 securityFirm = 6; //security firm, refer to SecurityFirm  
optional int32 simAccType = 7; //simulate account type, see SimAccType  
optional string uniCardNum = 8; //Universal account number  
optional int32 accStatus = 9; //Account status, refer to TrdAccStatus  
optional int32 accRole = 10; //Account Structure, used to distinguish between repeated int32 jpAccType = 11; //JP sub account type, refer to TrdSubAccType 
```

# Account Funds


Funds


message Funds   
{ required double power $= 1$ //Maximum Buying Power (Minimum OpenD version require required double totalAssets $= 2$ //Net Assets required double cash $= 3$ //Cash (Only Single market accounts use this field. required double marketVal $= 4$ //Securities Market Value (only applicable to see required double frozenCash $= 5$ //Funds on Hold required double debtCash $= 6$ //Interest Charged Amount (Minimum OpenD version required double avlWithdrawalCash $= 7$ //Withdrawable Cash (Only Single market optional int32 currency $= 8$ //The currency used for this query (only optional double availableFunds $= 9$ //Available funds (only applicable to optional double unrealizedPL $= 10$ //Unrealized gain or loss (only applicable optional double realizedPL $= 11$ //Realized gain or loss (only applicable optional int32 riskLevel $= 12$ //Risk control level (only applicable optional double initialMargin $= 13$ //Initial Margin (only applicable to optional double maintenanceMargin $= 14$ //Maintenance Margin (Minimum OpenD version repeated AccCashInfo cashInfoList $= 15$ //Cash information by currency (only a optional double maxPowerShort $= 16$ //Short Buying Power (Minimum OpenD version optional double netCashPower $= 17$ //Cash Buying Power (Only Single market ad optional double longMv $= 18$ //Long Market Value (Minimum OpenD version optional double shortMv $= 19$ //Short Market Value (Minimum OpenD version optional double pendingAsset $= 20$ //Asset in Transit (Minimum OpenD version optional double maxWithdrawal $= 21$ //Maximum Withdrawal (only applicable optional int32 riskStatus $= 22$ //Risk status (only applicable to optional double marginCallMargin $= 23$ //Margin-call Margin (Minimum Open 

```txt
28 optional bool isPdt = 24; //Is it marked as a PDT. True: It is a   
29 optional string pdtSeq = 25; //Day Trades Left. Only applicable to   
30 optional double beginningDTBP = 26; //Beginning DTBP. Only applicable to s   
31 optional double remainingDTBP = 27; //Remaining DTBP. Only applicable to s   
32 optional double dtCallAmount = 28; //Day-trading Call Amount. Only applic   
33 optional int32 dtStatus = 29; //Day-trading Status. Only applic   
34   
35 optional double securitiesAssets = 30; // Net asset value of securities   
36 optional double fundAssets = 31; // Net asset value of fund   
37 optional double bondAssets = 32; // Net asset value of bond   
38   
39 repeated AccMarketInfo marketInfoList = 33; //Account assets information by mark   
40 } 
```

# Account Holding


Position


1 message Position   
2 {   
3 required uint64 positionID $= 1$ //Position ID, a unique identifier of a posit   
4 required int32 positionSide $= 2$ //Position direction, refer to the enumeration   
5 required string code $= 3$ //Code   
6 required string name $= 4$ //Name   
7 required double qty $= 5$ //Holding quantity, 2 decimal places, the same below   
8 required double canSellQty $= 6$ //Available quantity. Available quantity $=$ H   
9 required double price $= 7$ //Market price, 3 decimal places, 2 decimal places   
10 optional double costPrice $= 8$ //Diluted Cost (for securities account). Avera   
11 required double val $= 9$ //Market value, 3 decimal places, value of this field   
12 required double plVal $= 10$ //Amount of profit or loss, 3 decimal places, 2   
13 optional double pLRatio $= 11$ //Percentage of profit or loss(under diluted co   
14 optional int32 secMarket $= 12$ //The market to which the securities belong, e   
15   
16 //The following is the statistics of this position today   
17 optional double td_plVal $= 21$ //Today's profit or loss, 3 decimal places, t   
18 optional double td_trdVal $= 22$ //Today's trading volume, not applicable for   
19 optional double td_buyVal $= 23$ //Total value bought today, not applicable for   
20 optional double td_buyQty $= 24$ //Total amount bought today, not applicable for   
21 optional double td_buyVal $= 25$ //Total value sold today, not applicable for   
22 optional double td_buyQty $= 26$ //Total amount sold today, not applicable for   
23 

```txt
optional double unrealizedPL = 28; //Unrealized profit or loss (only applicable)  
optional double realizedPL = 29; //Realized profit or loss (only applicable)  
optional int32 currency = 30; // Currency type, refer to Currency  
optional int32 trdMarket = 31; // Trading market, refer to the enumeration de  
optional double dilutedCostPrice = 32; //diluted cost price, applicable for  
optional double averageCostPrice = 33; //average cost price, not applicable  
optional double averagePlRatio = 34; //Percentage of profit or loss(under a 
```

# Order


Order


```txt
message Order { 
```

```csv
required int32 trdSide = 1; //Trading direction, refer to TrdSide enumeration  
required int32梯队Type = 2; //Order type, refer to enumeration definition  
required int32 orderStatus = 3; //Order status, refer to enumeration definition  
required uint64 orderID = 4; //Order number  
required string orderIDEx = 5; //Extended order number (only for checking the)  
required string code = 6; //code  
required string name = 7; //Name  
required double qty = 8; //Order quantity, 3 decimal places, option unit is  
optional double price = 9; //Order price, 3 decimal places  
required string createTime = 10; //Create time, strictly in accordance with  
required string updateTime = 11; //The last update time, strictly according  
optional double fillQty = 12; //Filled quantity, 2 decimal place accuracy, the  
optional double fillAvgPrice = 13; //Average price of the fill, no precision  
optional string lastErrMsg = 14; //The last error description, if there is an  
optional int32 secMarket = 15; //The market to which the securities belong, a  
optional double createTimestamp = 16; //Timestamp for creation  
optional double updateTimestamp = 17; //Timestamp for last update  
optional string remark = 18; //User remark string, the maximum length is 64  
optional double auxPrice = 21; //Trigger price  
optional int32梯队Type = 22; //Trailing type, see Trd/Common.TrailType enu  
optional double trailValue = 23; //Trailing amount / ratio  
optional double trailSpread = 24; //Specify spread  
optional int32 currency = 25; // Currency type, refer to Currency  
optional int32 trdMarket = 26; //Trading market, refer to the enumeration de  
optional int32 session = 27; //Trading session, refer to the enumeration def
```

28 29 

```txt
optional int32 jpAccType = 28; //JP sub account type, refer to TrdSubAccType } 
```

# Order Fee Item


OrderFeeItem


1 message OrderFeeItem   
2 {   
3 optional string title $=$ 1; //Fee title   
4 optional double value $=$ 2; //Fee Value   
5 } 

# Order Fee


OrderFee


1 message OrderFee   
2 {   
3 required string orderIDEx $= 1$ //Server order id   
4 optional double feeAmount $= 2$ //Fee amount   
5 repeated OrderFeeItem feeList $= 3$ //Fee details   
6 } 

# Order Fill


OrderFill


1 message OrderFill   
2 {   
3 required int32 trdSide $= 1$ ; //Trading direction, refer to enumeration definite   
4 required uint64 fillID $= 2$ ; //OrderFill ID   
5 required string fillIDEx $= 3$ ; //Extended OrderFill ID (only for checking the   
6 optional uint64 orderID $= 4$ ; //Order ID 

7 optional string orderIDEx $= 5$ //Extended order ID (only when checking the p  
8 required string code $= 6$ //code  
9 required string name $= 7$ //Name  
10 required double qty $= 8$ //Filled quantity, 2 decimal place accuracy, the opt  
11 required double price $= 9$ //Price of the fill, 3 decimal places  
12 required string createTime $= 10$ //Create time (transaction time), in strict  
13 optional int32 counterBrokerID $= 11$ //Counter Broker ID, valid for Hong Kong  
14 optional string counterBrokerName $= 12$ //Counter Broker Name, valid for Hong  
15 optional int32 secMarket $= 13$ //Securities belong to the market, refer to en  
16 optional double createTimestamp $= 14$ //Create a timestamp  
17 optional double updateTimestamp $= 15$ //last update timestamp  
18 optional int32 status $= 16$ //Deal status, refer to enumeration definition o  
19 optional int32 trdMarket $= 17$ //Trading market, refer to enumeration defini  
20 optional int32 jpAccType $= 18$ //JP sub account type, refer to TrdSubAccType  
21 } 

# Maximum Trading Quantity


MaxTrdQtys


1 message MaxTrdQtys   
2 {   
3 //Due to the current server's implementation, it is required to sell the hold   
4 required double maxCashBuy $= 1$ ;//Buy on cash. (Maximum quantity that can be   
5 optional double maxCashAndMarginBuy $= 2$ ;//Buy on margin. (Maximum quantity   
6 required double maxPositionSell $= 3$ ;//Sell on position. (Maximum quantity ca   
7 optional double maxSellShort $= 4$ ;//Short sell. (Maximum quantity can be sold   
8 optional double maxBuyBack $= 5$ ;//Short positions. (Buyback required quantity   
9 optional double longRequiredIM $= 6$ //Initial margin change when buy   
10 optional double shortRequiredIM $= 7$ //Initial margin change when sell   
11 } 

# Cash Flow Summary Info


FlowSummaryInfo


```txt
1 message FlowSummaryInfo 2 { 
```

3 optional string clearingDate $= 1$ //clearing date   
4 optional string settlementDate $= 2$ //settlement date   
5 optional int32 currency $= 3$ //currency   
6 optional string cashFlowType $= 4$ //cash flow type   
7 optional int32 cashFlowDirection $= 5$ //cash flow direction, refer to TrdCas   
8 optional double cashFlowAmount $= 6$ //amount   
9 optional string cashFlowRemark $= 7$ //remark   
10 optional uint64 cashFlowID $= 8$ //cash flow ID   
11 } 

# Filter Conditions


TrdFilterConditions


message TrdFilterConditions   
{ repeated string codeList $= 1$ ;//Code filtering,only returns the products for repeated uint64 idList $= 2$ //ID primary key filter,only returns the products optional string beginTime $= 3$ //Start time,strictly in accordance with YYYY-Id optional string endwhile $= 4$ //The end time,strictly in accordance with YYYY-Id repeated string orderIDExList $= 5$ // The server order id list,which can be us optional int32 filterMarket $= 6$ //Trading market filter,refer to enumeration } 

# Basic Functions

# Set Interface Information(deprecated)

```txt
set_client_info(client_id, client_ver) 
```

Introduction 

Set calling interface information (unnecessary). 

. Parameters 

client_id: the identification of the client 

client_ver: the version number of the client 

Example 

```python
1 from futu import *
2 SysConfig.set_client_info("MyFutuAPI", 0)
3 quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)
4 quoteCtx.close()
```
```java 
```

# Set Protocol Format

```txt
setProto fmt(proto fmt) 
```

Introduction 

Set the communication protocol body format, Protobuf and Json formats are currently supported , default ProtoBuf, unnecessary interface 

Parameters 

proto_fmt: protocol format, refer to ProtoFMT 

Example 

```python
1 from futu import *
2 SysConfig.set Proto fmt(ProtoFMT.Protobuf)
3 quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111)
4 quoteCtx.close() 
```

# Set Protocol Encryption Globally

Introduction Setting protocol encryption can help users protect their requests and returned contents globally. For more information about Protocol Encryption Process, please check here. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>is Encrypt</td><td>bool</td><td>Enable encryption or not.</td></tr></table>

Example 

1 from futu import \*   
2 SysConfig enabling.proto_encrypt(True)   
3 SysConfig.set_init_rsa_file("conn_key.txt") # rsa private key file path   
4 quoteCtx $=$ OpenQuoteContext(host $= 1$ 127.0.0.1'，port $= 11111$ 5 quoteCtx.close() 

# Set the Path of Private Key

set_init_rsa_file(file) 

Introduction 

Set the Path of Private Key in Futu API. For more information about Protocol Encryption Process, please check here. 

Parameters 

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>file</td><td>str</td><td>Private key file path.</td></tr></table>

. Example 

1 from futu import \*   
2 SysConfig enabling.proto_encrypt(True)   
3 SysConfig.set_init_rsa_file("conn_key.txt") # rsa private key file path   
4 quoteCtx $=$ OpenQuoteContext(host $= 1$ 127.0.0.1'，port $= 11111$ 5 quoteCtx.close() 

# Set Thread Mode

set_all_thread_daemon(all_daemon) 

Introduction Whether to set all internally threads to be daemon threads. 

If it is set to be daemon threads, then after the main thread exits, the process also exits. 

For example, when using the real-time callback API, you need to make sure the main thread survives by yourself. Otherwise, when the main thread exits, the process also exits and you will no longer receive the push data. 

If it is set to a non-daemon thread, the process will not exit after the main thread exits. For example, if you do not call close() to close the connection after creating a quote or trade object, the process will not exit even if the main thread exits. 

# Parameters

<table><tr><td>Parameter</td><td>Type</td><td>Description</td></tr><tr><td>all Daemon</td><td>bool</td><td>Whether to set threads to be daemon threads.</td></tr></table>

# Example

from futu import * 

SysConfig.set_all_thread_daemon(True)2 

3 quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111) 

# the process will exit without calling quote_ctx.close(),4 

# Set Callback

set_handler(handler) 

# Introduction

Set asynchronous callback processing object 

# Parameters

handler: callback processing object 

<table><tr><td>Class</td><td>Description</td></tr><tr><td>SysNotifyHandlerBase</td><td>OpenD notification processing base class</td></tr><tr><td>StockQuoteHandlerBase</td><td>Quote processing base class</td></tr><tr><td>OrderBookHandlerBase</td><td>Order book processing base class</td></tr><tr><td>CurKlineHandlerBase</td><td>Real-time candlestick processing base class</td></tr><tr><td>TickerHandlerBase</td><td>Tick-By-Tick processing base class</td></tr><tr><td>RTDataHandlerBase</td><td>Time Frame data processing base class</td></tr><tr><td>BrokerHandlerBase</td><td>Broker queue processing base class</td></tr><tr><td>PriceReminderHandlerBase</td><td>Price reminder processing base class</td></tr><tr><td>TradeOrderHandlerBase</td><td>Order processing base class</td></tr><tr><td>TradeDealHandlerBase</td><td>Order fill processing base class</td></tr></table>


Example


1 import time   
2 from futu import \*   
3 class OrderBookTest(OrderBookHandlerBase):   
4 def on_recv_rsp(self, rsp Pb):   
5 ret_code，data $=$ super(OrderBookTest,self).on_recv_rsp(rsp_pb)   
6 if ret_code != RET_OK:   
7 print("OrderBookTest: error，msg:%s"% data)   
8 return RET_ERROR，data   
9 print("OrderBookTest"，data)# OrderBookTest's own processing logic   
10 return RET_OK，data   
11 quoteCtx $=$ OpenQuoteContext(host='127.0.0.1'，port=11111)   
12 handler $=$ OrderBookTest()   
13 quoteCtx.sethandler(handle) # Setting real-time order book callback   
14 quoteCtx.subscribe(['HK.00700']，[SubType.ORDERTABLE]) # Subscribe to the order book type, OpenD st   
15 time.sleep(15)# Set the script to receive OpenD push duration to 15 seconds   
16 quoteCtx.close() # Close the current connection, OpenD will automatically cancel the subscription o 

# Get Connection ID

get_sync_conn_id() 

Introduction 

Get the connection ID, the value will be available after the connection is successfully initialized 

. Return 

conn_id: connection ID 

Example 

1 from futu import \*   
2 quote_ctx $=$ OpenQuoteContext(host $= 1$ 27.0.0.1'，port $= 1$ 11111   
3 quote_ctx.get_sync_connect_id()   
4 quote_ctx.close() # After using the connection, remember to close it to prevent the number of conn 

# SysNotifyHandlerBase

Introduction 

Notify OpenD of some important news, such as disconnection, etc. 

. Protocol ID 

1003 

Return 

<table><tr><td>Field</td><td>Type</td><td>Description</td></tr><tr><td>ret</td><td>int</td><td>Returned value. On success, ret == RET_OK. On error, ret != RET_OK.</td></tr><tr><td rowspan="2">data</td><td>tuple</td><td>If ret == RET_OK, event notification data is returned.</td></tr><tr><td>str</td><td>If ret != RET_OK, error description is returned.</td></tr></table>

The format of event notification data is as follows: 

<table><tr><td>Field</td><td>Type</td><td>Description</td><td></td></tr><tr><td>notify_type</td><td>SysNotifyType</td><td>Notification data type</td><td></td></tr><tr><td rowspan="3">sub_type</td><td>ProgramStatusType</td><td>Subtype. If notify_type == SysNotifyType.PROGRAM_STATUS, program status type is returned.</td><td></td></tr><tr><td>GtwEventType</td><td>1581</td><td>Subtype. If notify_type == SysNotifyType.GTW_EVENT, OpenD event type is returned.</td></tr><tr><td>0</td><td>If notify_type != SysNotifyType.PROGRAM_STATUS and notify_type != SysNotifyType.GTW_EVENT, no useful information is returned.</td><td></td></tr><tr><td>msg</td><td>dict</td><td>Event information. If notify_type == SysNotifyType.CONN_STATUS,</td><td></td></tr></table>

<table><tr><td rowspan="2"></td><td rowspan="2"></td><td>connection status event information is returned.</td></tr><tr><td>Event information. If notify_type == SysNotifyType.QOT_RIGHT, quote right event information is returned.</td></tr></table>

The format of connection status event information is as follows(The value of connection status is a bool type, with True for normal, and False for disconnected): 

```txt
1 { 'qot_logged': bool1,   
2 3 'trd_logged': bool2,   
4 } 
```

The format of quote right event information is as follows(the type of quote right refers to Quote Right): 

```txt
1 {  
2 'hk_qot_right': value1,  
3 'hk_option_qot_right': value2,  
4 'hk_future_qot_right': value3,  
5 'us_qot_right': value4,  
6 'us_option_qot_right': value5,  
7 'us_future_qot_right': value6, // deprecated  
8 'cn_qot_right': value7,  
9 'us_index_qot_right': value8,  
10 'us_ota_cqot_right': value9,  
11 'sg_future_qot_right': value10,  
12 'jp_future_qot_right': value11,  
13 'us_future_qot_right_cme': value12,  
14 'us_future_qot_right_cbot': value13,  
15 'us_future_qot_right_nymex': value14,  
16 'us_future_qot_right_comex': value15,  
17 'us_future_qot_right_cboe': value16,  
18 } 
```

Example 

```python
1 import time
2 from futu import *
3
4 class SysNotifyTest(SysNotifyHandlerBase):
5 def on_recv_rsp(self, rsp_str):
6 ret_code, data = super(SysNotifyTest, self).on_recv_rsp(rsp_str)
7 notify_type, sub_type, msg = data 
```

```python
if ret_code != RET_OK: logger.debug("SysNotifyTest: error, msg: {}.format(msg)) return RET_ERROR, data if (notify_type == SysNotifyType.GTW_EVENT): # OpenD event notification print("GTW_EVENT, type: {} msg: {}.format(sub_type, msg)) elif (notify_type == SysNotifyType.PROGRAM_STATUS): # Notification of change in program sta print("PROGRAM_STATUS, type: {} msg: {}.format(sub_type, msg)) elif (notify_type == SysNotifyType.CONN_STATUS): ## Notification of change in connection sta print("CONN_STATUS, qot: {}.format(msg['qot_logged'])) print("CONN_STATUS, trd: {}.format(msg['trd_logged'])) elif (notify_type == SysNotifyType.QOT_RIGHT): # Notification of change in quote right print("QOT_RIGHT, hk:{}.format(msg['hk_qot_right'])) print("QOT_RIGHT, hk_option:{}.format(msg['hk_option_qot_right'])) print("QOT_RIGHT, hk_future:{}.format(msg['hk_future_qot_right'])) print("QOT_RIGHT, us:{}.format(msg['us_qot_right'])) print("QOT_RIGHT, us_option:{}.format(msg['us_option_qot_right'])) print("QOT_RIGHT, us_future:{}.format(msg['us_future_qot_right ]).print("QOT_RIGHT, cn:{}.format(msg['cn_qot_right'])) print("QOT_RIGHT, us_index:{}.format(msg['us_index_qot_right'])) print("QOT_RIGHT, us_otc:{}.format(msg['us_otc_qot_right')); print("QOT_RIGHT, sg_future:{}.format(msg['sg_future_qot_right']); print("QOT_RIGHT, jp_future:{}.format(msg['jp_future_qot_right ]); print("QOT_RIGHT, us_future_cme:{}.format(msg['us_future_qot_right_cme']; print("QOT_RIGHT, us_future_cbot:{}.format(msg['us_future_qot_right_cbot')); print("QOT_RIGHT, us_future_nymex:{}.format(msg['us_future_qot_right_nymex']; print("QOT_RIGHT, us_future_comex:{}.format(msg['us_future_qot_right_comex']; print("QOT_RIGHT, us_future_cboe:{}.format(msg['us_future_qot_right_cboe'])) return RET_OK, data quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111) handler = SysNotifyTest() quoteCtx.setCTXhandler (# Set real-time swing callback time.sleep(15) # Set the script to receive OpenD push duration to 15 seconds quoteCtx.close() # After using the connection, remember to close it to prevent the number of conn 
```

# General Definitions

# Interface Result

RET_CODE 

? RET_OK 

Success 

? RET_ERROR 

Failed 

# Protocol Format

ProtoFMT 

. Protobuf 

Google Protobuf 

. Json 

Json 

# Packet Encryption Algorithm

# Program Status Type

ProgramStatusType 

NONE 

Unknown 

. LOADED 

The necessary modules have been loaded 

. LOGING 

Logging in 

. NEED_PIC_VERIFY_CODE 

Need graphic verification code 

NEED_PHONE_VERIFY_CODE 

Need mobile phone verification code 

LOGIN_FAILED 

Login failed 

FORCE_UPDATE 

The client version is too low 

NESSARY_DATA_PREPARING 

Pulling necessary information 

. NESSARY_DATA_MISSING 

Missing necessary information 

UN_AGREE_DISCLAIMER 

Disclaimer is not agreed 

READY 

Ready to use 

. FORCE_LOGOUT 

OpenD was forced to log out 

# OpenD Event Notification Type

# GtwEventType

. LocalCfgLoadFailed 

Failed to load the local configuration file 

APISvrRunFailed 

Failed to run the OpenD monitoring service 

. ForceUpdate 

Force upgrade of the OpenD 

. LoginFailed 

Failed to log in to Futu servers 

. UnAgreeDisclaimer 

Did not agree to the disclaimer, unable to run 

. LOGIN_FAILED 

Login failed 

. NetCfgMissing 

Missing network connection configuration 

. KickedOut 

Login kicked offline 

? LoginPwdChanged 

Login password has been changed 

. BanLogin 

This account is not allowed to log in by Futu servers 

. NeedPicVerifyCode 

Need graphic verification code 

. NeedPhoneVerifyCode 

Need mobile verification code 

AppDataNotExist 

Program package data loss 

. NessaryDataMissing 

The necessary data is not synchronized successfully 

TradePwdChanged 

Transaction password change notice 

EnableDeviceLock 

Need to enable device lock 

# System Notification Type

SysNotifyType 

. GTW_EVENT 

Gateway event 

. PROGRAM_STATUS 

Program status changes 

. CONN_STATUS 

Status of Connection to Futu servers has been changed 

. QOT_RIGHT 

Quotes authority changed 

# Package Unique Identifier

1 message PacketID   
2 {   
3 required uint64 connID $=$ 1; //The current TCP connection ID, the unique identi   
4 required uint32 serialNo $= 2$ ; //Increment serial number   
5 } 

# Program Status


ProgramStatus


1 message ProgramStatus   
2 {   
3 required Program statuses type type $= 1$ //Current status   
4 optional string strExtDesc $= 2$ //Additional description   
5 } 

# Protocol Introduction

Futu API is an API SDK, encapsulated by Futu including mainstream programming languages (Python, Java, C #, ${ \mathsf { C } } + + ,$ JavaScript) to make it easy for you to call and reduce the difficulty of trading strategy development. 

This part mainly introduces the underlying protocol of communication between script and OpenD service, which is suitable for users who do not use the above five programming languages. 

# Tips

If you are using a programming language that is one of the five mainstream programming languages mentioned above, you can skip this part. 

# Protocol Request Process

Create a connection 

. Initialize the connection 

. Request data or receive pushed data 

Send KeepAlive protocol periodically to keep connected 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/c47b7085420941bd16178f28a98158b47913e86d7558df98506197bc10937d50.jpg)


# Protocol Design

The protocol data includes the protocol header and the protocol body. The protocol header is fixed, and the protocol body is determined according to the specific protocol. 

# Protocol Header

```c
struct APIProtoHeader {
    u8_t szHeaderFlag[2];
    u32_t nProtoID;
    u8_t nProtoFmtType;
    u8_t nProtoVer;
    u32_t nSerialNo;
    u32_t nBodyLen;
    u8_t arrBodySHA1[20]; 
```

<table><tr><td>Field</td><td>Description</td></tr><tr><td>szHeaderFlag</td><td>Packet header start flag, fixed as &quot;FT&quot;</td></tr><tr><td>nProtoID</td><td>Protocol ID</td></tr><tr><td>nProtoFmtType</td><td>Protocol type, 0 for Protobuf, 1 for Json</td></tr><tr><td>nProtoVer</td><td>Protocol version, used for iterative compatibility, currently 0</td></tr><tr><td>nSerialNo</td><td>Packet serial number, used to correspond to the request packet and return packet, and it is required to be incremented</td></tr><tr><td>nBodyLen</td><td>Body length</td></tr><tr><td>arrBodySHA1</td><td>SHA1 hash value of the original data of the packet body (after decryption)</td></tr><tr><td>arrReserved</td><td>Reserved 8-byte extension</td></tr></table>

# Tips

u8_t refer to 8-bit unsigned integer, u32_t refer to 32-bit unsigned integer 

OpenD internal processing uses Protobuf, so the protocol format recommends using Protobuf, to reduce Json conversion overhead. 

The nProtoFmtType field specifies the data type of the package body, and the corresponding protocol type will be returned when the package is returned. The data type of the push protocol is specified by the OpenD configuration file 

. arrBodySHA1 is used to verify the consistency of the requested data before and after network transmission, and must be filled in correctly 

The binary stream of the protocol header uses little-endian byte order, that is, generally there is no need to use ntohl and other related functions to convert the data 


Packet Body Structure of Protobuf Request


1 message C2S   
2 {   
3 required int64 req $= 1$ .   
4 }   
5   
6 message Request   
7 {   
8 required C2S c2s $= 1$ .   
9 } 


Packet Body Structure of Protobuf Response


1 message S2C   
2 {   
3 required int64 data $= 1$ .   
4 }   
5   
6 message Response   
7 {   
8 required int32�� $= 1$ [default $= -400]$ ; //RetType, result of return   
9 optional string retMsg $= 2$ 10 optional int32 errCode $= 3$ 11 optional S2C s2c $= 4$ 12 } 

<table><tr><td>Field</td><td>Description</td></tr><tr><td>c2s</td><td>Request parameter structure</td></tr><tr><td>req</td><td>Request parameters, actually defined according to the protocol</td></tr><tr><td>retType</td><td>Request result</td></tr><tr><td>retMsg</td><td>The reason for the failed request</td></tr><tr><td>errCode</td><td>The corresponding error code for failed request</td></tr><tr><td>s2c</td><td>Response data structure, some protocols do not return data if there is no such field</td></tr><tr><td>data</td><td>Response data, actually defined according to the protocol</td></tr></table>

# Tips

The package body format type request package is specified by nProtoFmtType field from protocol header, and the OpenD initiative push format is set in InitConnect. 

The original protocol file format is defined in Protobuf format. If you need json format transmission, it is recommended to use the protobuf3 interface to directly convert to json. 

The enumeration value field definition uses signed integer, and the comment indicates the corresponding enumeration. The enumeration is generally defined in Common.proto, Qot_Common.proto, Trd_Common.proto files. 

The price, percentage and other data in the protocol are transmitted in floating point type. Direct use will cause accuracy problems. It needs to be rounded according to the accuracy (if not specified in the protocol, the default is 3 decimal places) before use. 

# Heartbeat Keep Alive

```proto
1 syntax = "proto2";
2 package KeepAlive;
3 option javapackage = "com.fetu.openapi.pb";
4 option gopackage = "github.com/fetuopen/ftapi4go/pb/keepalive";
5 import "Common.proto";
6 message C2S
7 {
8 required int64 time = 1; //Greenwich timestamp when the client sends the pad
10 } 
```

```txt
14 {  
15 required int64 time = 1; //Greenwich timestamp when the server returned the  
16 }  
17  
18 message Request  
19 {  
20 required C2S c2s = 1;  
21 }  
22  
23 message Response  
24 {  
25 required int32(retType = 1 [default = -400]; //RetType, return result  
26 optional string retMsg = 2;  
27 optional int32 errCode = 3;  
28  
29 optional S2C s2c = 4;  
30 } 
```

Introduction 

Heartbeat keep alive 

? Protocol ID 

1004 

. Introduction 

According to the heartbeat keeping alive interval returned by the initialization protocol, send the heartbeeat keep alive protocol to OpenD. 

# Encrypted Communication Process

If OpenD is configured with encryption, InitConnect must use RSA public key encryption to initialize the connection protocol, and other subsequent protocols use the random key returned by InitConnect for AES encrypted communication. 

The encryption process of OpenD draws on the SSL protocol. Considering that services and applications are generally deployed locally, we simplifies the related processes. OpenD shares the same RSA private key file with the access Client. Please save and distribute the private key file properly. 

Go to this URL to generate a random RSA key pair online. The key format must be PCKS#1, the key length can be 512, 1024, and do not set password. Copy and save the generated private key to a file, and then configure the path of the private key file to the rsa_private_key configuration item agreed upon in OpenD Configuration. 

It is recommended that users who have real trade configure encryption to avoid leakage of account and trade information. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/46d71c136682b603279342c646e5bb23190b093c2bab88f7d94a66dc60ae2002.jpg)


# RSA Encryption and Decryption

OpenD configuration Convention rsa_private_key is the path of the private key file 

. OpenD shares the same private key file with the access client 

RSA encryption and decryption is only used for InitConnect requests, and is used to securely obtain symmetric encryption key of other request protocols 

The RSA key of OpenD is 1024-bit, the filling method is PKCS1, public key encryption, private key decryption, public key can be generated by private key 

# Send Data Encryption

RSA encryption rules: If the number of key bits is key_size, the maximum length of a single encryption string is (key_size)/8-11. The current number of bits is 1024, and the length of 

one encryption can be set to 100. 

Divide the plaintext data into one or several segments of up to 100 bytes for encryption, and the final encrypted data is spliced by all segmented encrypted data. 

# Receive Data Decryption

RSA decryption also follows the segmentation rule. For a 1024-bit key, the length of each segment to be decrypted is 128-byte. 

Divide the ciphertext data into one or several segments of up to 128 bytes for decryption, and the final decrypted data is spliced by all segmented decrypted data. 

# AES Encryption and Decryption

. The encryption key is returned by the InitConnect protocol 

. The ecb encryption mode of AES is used by default. 

# Send Data Encryption

AES encryption requires that the length of the source data must be an integer multiple of 16, so it needs to be aligned with $' 0 ^ { \prime }$ before encryption. Record mod_len for source data length and 16 module. 

Because it is possible to modify the source data before encryption, it is necessary to add a 16-byte padding data block at the end of the encrypted data. The last byte is assigned mod_len, and the remaining bytes are assigned the value '0'. The encrypted data and additional populated data blocks are spliced as the body data to be sent in the end. 

# Receive Data Decryption

For protocol body data, first take out the last byte and record it as mod_len, then truncate the body to the 16-byte padding data block before decrypting it (corresponding to the encrypted padding extra data block logic). 

When mod_len is 0, the above decrypted data is the body data returned by the protocol, otherwise the tail (16-mod_len) length of the data used for filling and alignment needs to be truncated. 

Data before encryption 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/977809912e8eb06aed20faea1051e4f37a9ecb7188cac46880641f00be2f0358.jpg)


When the original data of the protocol packet body is an integer multiple of 16,there is no such part 

Data after AES encryption 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/67ccbc380168bc67d96f8eaf3c1833f75955aa292876892b31a7b13850fadd24.jpg)


Package body after treatment 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/6891511958334df1e08c83ae192bd7dc140165c3dd8cfba9235a25cc4bb4523d.jpg)


Protocol packet bodyraw data 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/7b5d0ce98a90a3b1df98ac96aa667173244b5fe6d9d323f4c1016185b327fd32.jpg)


Fill with data ‘\0' 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/0aad18c311b0494fa8e2943ed4bc7bb11b473047cdede666e9b4bd4a4da9914e.jpg)


Encrypted data 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/86701972c836f8850eec4c66df30a3a45118bd518c6b867ead562490cfd070ee.jpg)


Source data length and 16 modulo value 

# OpenD Related

# Q1: OpenD automatically exited due to failure to complete "Questionnaire Evaluation and Agreement Confirmation"

A: You need to carryout relevant questionnaire evaluation and agreement confirmation before you can use OpenD. Please go to complete . 

# Q2: OpenD exited due to "the program's own data does not exist"

A: Generally, the copy of the own data fails due to permission problems. You can try to copy the file extracted from Appdata.dat in the program directory to the program data directory. 

Windows program data directory: %appdata%/com.futunn.FutuOpenD/F3CNN 

Non-windows program data directory: ~/.com.futunn.FutuOpenD/F3CNN 

# Q3: OpenD service failed to start

A: Please check: 

1. Whether there are other programs occupying the configured port; 

2. Is there a OpenD configured with the same port already running? 

# Q4: How to verify the mobile phone verification code?

A: On the OpenD interface or remotely to the Telnet port, enter the command ʻinput_phone_verify_code -code $= 1 2 3 4 5 6 ^ { \circ }$ . 

# Tips

123456 is the mobile phone verification code received 

# Q5: Are other programming languages supported?

A: OpenD provides a socket-based protocol. Currently we provide and maintain Python, $C + + ,$ Java, C# and JavaScript interfaces, download entry . 

If the above languages still cannot meet your needs, you can connect to the Protobuf protocol by yourself. 

# Q6: Verify the device lock multiple times on the same device

A: The device ID is randomly generated and stored in the \com.futunn.OpenD\F3CNN\Device.dat file. 

# Tips

1. If the file is deleted or damaged, OpenD will regenerate a new device ID and then verify the device lock. 

2. In addition, users of mirror copy deployment need to be aware that if the Device.dat content of multiple machines is the same, it will also cause these machines to verify the device lock multiple times. Delete the Device.dat file to solve it. 

# Q7: Does OpenD provide a Docker image?

A: Not currently available. 

# Q8: Can one account log in to multiple OpenD?

A: One account can log in to OpenD or other client terminals on multiple machines, and up to 10 OpenD terminals are allowed to log in at the same time. At the same time, there is a restriction of "market kicking", and only one OpenD can obtain the highest authority market. 

For example, if two terminals log into the same account, there can only be one HK stock LV2 quotation and the other HK stock BMP quotation. 

# Q9: How to control the market permissions of OpenD and other clients (desktop and mobile)?

A: In accordance with the regulations of the exchange, there will be a restriction on “market kicking” when multiple terminals are online at the same time, and only one terminal can obtain the highest authority market. The auto_hold_quote_right parameter is built-in in the startup parameters of the command line version of OpenD, which is used to flexibly configure market permissions. When this parameter option is enabled, OpenD will automatically retrieve it after the market permission is robbed. If it is robbed again within 10 seconds, other terminals will obtain the highest market quotation authority (OpenD will not rob again). 

# Q10: How to give priority to the OpenD market authority?

A: 

1. Configure the OpenD startup parameter auto_hold_quote_right to 1; 

2. Make sure not to grab the highest authority twice in a row within 10 seconds on the mobile or desktop Futubull (login counts once, and click "Restart Quotes" to count the second time). 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/6dc50c757475af41bae0ea8c0d313548f6fa793555457ac8b71681a19b264a98.jpg)


Q11: How to give priority to the market authority of the mobile terminal (or desktop terminal)? 

A: Set OpenD startup parameter auto_hold_quote_right to 0, and login with mobile or PC Futubull after OpenD. 

# Q12: Use the Visualization OpenD to remember the password to log in. After a long time hang up, it prompts that the connection is disconnected. Do I need to log in again?

A: Using the Visualization OpenD, if you choose to remember the password to log in, you will use the token recorded locally. Due to the time limit of the token, when the token expires, if there is network fluctuation or moomoo background release, it may cause the situation that it cannot be automatically connected after disconnecting from the background. Therefore, if you want visiulization OpenD for a long time to hang up, it is recommended to manually enter the password to log in, and OpenD will automatically handle this situation. 

# Q13: How to request official engineers to investigate logs when encountering product defects?

A: Communicate the issue with customer service, providing details such as: the time when the error occurred, OpenD version number, API version number, script language name, interface name or protocol number, and short code or screenshots containing detailed input parameters and returns. 

After customer service confirms it's a product defect, if further log investigation is needed, development engineers will proactively contact you. 

Some issues may require OpenD logs to help locate and confirm the problem. For tradingrelated issues, info log level is needed; for market-data-related issues, debug log level is required. The log level (log_level) can be configured in OpenD.xml . After configuration, OpenD needs to be restarted for the changes to take effect. Once the issue is reproduced, package that section of the log and send it to Futu's development engineers. 

# Tips

The log path is as follows: 

windows: %appdata%/com.futunn.FutuOpenD/Log 

# Q14: Script cannot connect to OpenD

A: Please try to check first: 

1. Whether the port connected by the script is consistent with the port configured by OpenD. 

2. Since the upper limit of OpenD connection is 128, is there any useless connection that is not closed? 

3. Check whether the listening address is correct. If the script and OpenD are not on the same machine, the OpenD listening address needs to be set to 0.0.0.0. 

# Q15: Disconnected after being connected for a while

A: If it is a self-docking protocol, check whether there is a regular heartbeat to maintain the connection. 

# Q16: I can't connect to OpenD when I run Python scripts in multiprocessing mode through the multiprocessing module under Linux?

A: After the process is created by default in the Linux/Mac environment, the thread created inside py-futu-api in the parent process will disappear in the child process, resulting in an internal program error. You can use spawn to start the process: 

1 

import multiprocessing as mp 

2 

mp.set_start_method('spawn') 

3 

p = mp.Process(target=func) 

py 

# Q17: How to log in to two OpenD at the same time on one computer?

A: Visualization OpenD does not support, but Command Line OpenD supports. 

1. Unzip the file downloaded from the official website, and copy the entire Command Line OpenD folder (e.g. OpenD_5.2.1408_Windows). Take Windows as an example, other systems can do the same operation. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/081b4ff1d8ad08c47b8bb1a1d9b7758f2a464b38dc488f5deb63e004f17c8e5a.jpg)


Futu_OpenD_7.2.3407_Windows 

Futu_OpenD-GUI_7.2.3407_Windows 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/c3d8c61ebdb107c4eb9dcc80ec849b45414e7882f84c0dc7f10b9567122f165c.jpg)


Futu_OpenD-GUI_7.2.3407_Windows.. 

2. Configure two OpenD.xml files that are placed in two Command Line OpenD folders. Configure items as follow: 

Configuration file 1: api_port $=$ 11111, login_account $=$ Login Account 1, login_pwd $=$ Login Password 1 

Configuration file 2: api_port $=$ 11112, login_account $=$ Login Account 2, login_pwd $=$ Login Password 2 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/d1522caced6672563c3463b1beff1941b24b4bc4bc197046e75c0defaf46fefc.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/b71248a6b1cead15d9db17f147294af9b7ad0cb93dc8d5ee71f734ffd422bed4.jpg)


3. Run the two OpenD.exe. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/9565e79b7b38ea78cc00ae0ff2daf2579f320eae3ba8c813a664ed419a80518e.jpg)


4. When calling the interface, note that the parameter port (OpenD listening address) should corresponds to the parameter api_port in the OpenD.xml file. 

For example: 

```python
1 from futu import *
2
3 # Send requests to OpenD logged in account 1
4 quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11111, is_encrypt=False)
5 quoteCtx.close() # After using the connection, remember to close it to prevent
6
7 # Send requests to OpenD logged in account 2
8 quoteCtx = OpenQuoteContext(host='127.0.0.1', port=11112, is_encrypt=False)
9 quoteCtx.close() # After using the connection, remember to close it to prevent 
```

Q18: How do I execute the operation and maintenance commands for grabbing permissions through scripts when the market permission is kicked off by other clients? 

A: 

1. Configure Telnet address and Telnet port. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/e434b36b9dbdbb7ddd70cb4bde506b1a3b958b3345afaf82f13035cf1a654504.jpg)


# Futu OpenD Login

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/dae685763e17fafbbda6057b1555e3de9893dfbb74a18f0f17bf9dd4535ce77d.jpg)


Remember Me 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/386ae56dde56e0cea30dc80c994b7f1fe15b758b696cffadeb0aacd9e207e98d.jpg)


# Basic

# Advanced

# Futu0penD.xm1区

```txt
1 <futu_open>   
2 <-- 基础参数 -->   
3 <-- Basic parameters -->   
4 <-- 协议监听地址，不填默认127.0.0.1 -->   
5 <-- Listening address. 127.0.0.1 if not specified --> // Listening address. 127.0.0.1 by default   
6 <ip>127.0.0.1</ip>   
7 <-- API接口协议监听端口 -->   
8 <-- API interface protocol listening port -->   
9 <api_port>11111</api_port>   
10 <-- 登录帐号 -->   
11 <login account>100000</login_account>   
12 <-- 登录密码32位MD5加密16进制 -->   
13 <-- <login pwd md5>6e55f158a827blalc432la245aaaad88</login pwd md5> -->   
14 <-- 登录密码明文，密码密文存在情况下只使用密文 -->   
15 <login pwd>123456</login pwd>   
16 <-- FutuOpenD语言，en：英文，chs：简体中文 -->   
17 <lang>chs</lang>   
18 <-- 进阶参数 -->   
19 <-- Advanced parameters -->   
20 <-- FutuOpenD日志等级，no, debug, info, warning, error, fatal -->   
21 <log_level>info</log_level>   
22 <-- API推送协议格式，0:pb，l:json -->   
23 <-- API push protocol format，0:pb，l:json -->   
24 <push proto_type>0</pushProto_type>   
25 <-- API订阅数据推送频率控制，单位毫秒，目前不包括k线和分时，不设置则不限制频率--->   
26 <-- API subscription data push frequency control, in milliseconds, currently does not include K-line and time-sharing, if not   
27 <--<gatishushfrequency>1000</gatishushrequency> -->   
28 <-- Telnet监听地址，不填默认127.0.0.1 -->   
29 <-- Telnet listening address, default 127.0.0.1 if not filled in --> // Telnet listening address, 127.0.0.1 by default   
30 <telnet_ip>127.0.0.1</telnet_ip>   
31 <-- Telnet监听端口 -->   
32 <-- Telnet listening port -->   
33 <telnet port>22222</telnet port>   
34 <-- API协议加密私钥文件路径，不设置则不加密 -->   
35 <-- API protocol encrypted private key file path, if not set, it will not be encrypted --> // File path for private key for   
36 <-- <rsa_private_key>D:\rsa</rsa_private_key> -->   
37 <-- 是否接收到价提醒推送，0：不接收，1：接收 -->   
38 <-- Whether to receive the price reminder push, 0: not receive, 1: receive -->
```

2. Start OpenD (it will also start Telnet). 

3. After finding that the market quotation authority has been robbed, you can refer to the following code example and send the request_highest_quote_right command to 

```python
1 from telnetlib import Telnet
2 with Telnet('127.0.0.1', 22222) as tn: # Telnet address is: 127.0.0.1, Telnet port
3 tn.write(b'request Highest quote_right\r\n')
4 reply = b'
5 while True:
6 msg = tn.read_until(b'\r\n', timeout=0.5)
7 reply += msg
8 if msg == b': break
9 print-replydecode('gb2312')) 
```

# Q19: OpenD automatic upgrade failed

A: The automatic update of OpenD failed to be executed by the update command. Possible reasons: 

The file is occupied by other processes: you can try to close other OpenD processes, or restart the system and execute update again If the above still cannot be solved, you can download the update by yourself through Official Website . 

# Q20: Fail to launch the visualization OpenD on ubuntu22？

A: When running the visualization OpenD on certain Linux distributions (such as Ubuntu 22.04), you may encounter the error: dlopen(): error loading libfuse.so.2 . This occurs because libfuse is not installed by default on these systems. Typically you can resolve this issue by installing libfuse manually. For example, you can install it via the commane line on Ubuntu22.04 with: 

```txt
1 sudo apt update 2 sudo apt install -y libfuse2 
```

Once successfully installed, you will be able to run the visualization OpenD normally. Please refer to https://docs.appimage.org/user-guide/troubleshooting/fuse.html for more details. 

# Q21: How to run the command line OpenD in the background on Linux?

A: First, switch to the directory where FutuOpenD is located, configure FutuOpenD.xml, and then execute the following command. 

1 

nohup ./FutuOpenD & 

# Quote related

# Q1: Subscription failed

A: When the subscription interface returns an error, there are two common situations. 

. Insufficient subscription quota 

Please refer to Subscription Quota & Historical Candlestick Quota for the subscription quota rules. 

. Insufficient quota right 

The quota right that supports subscription are shown in the following table: 

<table><tr><td>Market</td><td>Contracts</td><td>Quota Right for Subscription</td></tr><tr><td rowspan="3">HK Market</td><td>Securities</td><td>LV1, LV2, SF</td></tr><tr><td>Options</td><td>LV1, LV2</td></tr><tr><td>Futures</td><td>LV1, LV2</td></tr><tr><td rowspan="3">US Market</td><td>Securities</td><td>LV1, LV2</td></tr><tr><td>Options</td><td>LV1</td></tr><tr><td>Futures</td><td>LV1, LV2</td></tr><tr><td>A-Share Market</td><td>Securities</td><td>LV1</td></tr></table>

Please refer to Quote Right for the access method. 

Note: If your account has the above-mantioned quota rights, but the subscription still fails. The possible reason is that the quota right has been kicked out by other terminals. 

# Q2: Unsubscribe failed

A: You can unsubscribe after you subscribe for at least one minute. 

# Q3: The unsubscribe was successful but the quota was not released

A: The quota is released after all connections are unsubscribed to the market. 

For example: Connection A and Connection B are both subscribing to HK.00700's listing data. After Connection A is unsubscribed, because Connection B is still calling HK.00700's listing data, the OpenD quota will not be released until all connections have been unsubscribed the listing data of HK.00700. 

# Q4: Will the quota be released if the script connection is closed if the subscription is less than one minute?

A: No. After the connection is closed, the target type whose subscription duration is less than one minute will be automatically unsubscribed after reaching one minute, and the corresponding subscription quota will be released. 

# Q5: What is the specific restriction logic for requesting frequency restriction?

A: At most n times within 30 seconds, it means that the interval between the first request and the $n + 1$ th request must be greater than 30 seconds. 

# Q6: What is the reason why self-selected stocks cannot be added?

A: Please check whether the upper limit is exceeded first, or delete part of the self-selected stocks. 

# Q7: Why is the US stock quotation on the OpenAPI side different from the national comprehensive quotation on the client side?

A: Since US stock trade are scattered on many exchanges, Futu provides two basic quotations for US stocks, one is Nasdaq Basic (quotes on the Nasdaq exchange), and the other is a comprehensive quotation for the United States (all 13 exchanges in the United States). 

However, OpenAPI's US stock quote currently only support Nasdaq Basic purchases through quotation card, and do not support comprehensive US quote. 

Therefore, if you purchase both the US comprehensive quotation card on the APP side and the Nasdaq Basic quotation card that is only used for OpenAPI, there may indeed be a difference in the quotation between the APP side and the OpenAPI side. 

Therefore, if you notice a discrepancy between the opening price of U.S. stocks and the price displayed on the App, this is because the OpenAPI real-time upstream market data only retrieves Nasdaq Basic. 

# Q8: Where can I buy OpenAPI quotation cards?

A: 

. HK market 

HK stocks LV2 advanced market (only non-Chinese mainland IP) 

HK stock options futures LV2 advanced market (only non-Mainland China IP) 

HK stocks LV2 $^ +$ option futures LV2 market (non-Mainland China IP only) 

HK Stocks Advanced Full Market Quotes (SF Quotes) 

US market 

US stocks Nasdaq Basic 

US stocks Nasdaq Totalview 

US options OPRA real-time data 

Q9: Why sometimes, the response of the get interface to obtain real-time data is slow? 

A: Because the get interface for real-time data needs to be subscribed first, and it depends on the push to OpenD from the background. If the user uses the get interface to request immediately after subscribing, OpenD may not receive the background push yet. In order to prevent this from happening, the get interface has built-in waiting logic, and the push will be returned to the script immediately after receiving the push within 3 seconds, and empty data will be returned to the script if the background push is not received for more than 3 seconds. The get interfaces include: get_rt_ticker, get_rt_data, get_cur_kline, get_order_book, get_broker_queue, get_stock_quote. Therefore, when you find that the response of the get interface for obtaining real-time data is relatively slow, you can first check whether it is the cause of no trade data. 

# Q10: What kind of data can be obtained after purchasing the OpenAPI Nasdaq Basic quotation card?

A: After the Nasdaq Basic quotation card purchase is activated, the categories that can be obtained include Nasdaq, NYSE, NYSE MKT stocks listed on the exchange (including US stocks and ETF, excluding US stock futures and US stock options). Supported data interfaces include: snapshots, historical candlestick, real-time ticker subscriptions, real-time one-stage subscriptions, real-time candlestick subscriptions, real-time quotation subscriptions, real-time Time Frame subscriptions, and price reminders. 

# Q11: How many levels does each market category support?


A:


<table><tr><td>Quotes category</td><td>LV1</td><td>LV2</td><td>SF</td></tr><tr><td>HK stocks (including Stock, Warrants, bulls and bears, and inbound securities)</td><td>/</td><td>10</td><td>full stock + thousand details</td></tr><tr><td>HK stock options futures</td><td>1</td><td>10</td><td>/</td></tr><tr><td>US stocks (including ETF)</td><td>1</td><td>60</td><td>/</td></tr><tr><td>US stock options</td><td>1</td><td>/</td><td>/</td></tr><tr><td>US futures</td><td>/</td><td>40</td><td>/</td></tr><tr><td>A-shares</td><td>5</td><td>/</td><td>/</td></tr></table>

# Q12：Why does OpenD still have no quote right after I purchase and activate the quotation card?

A: 

1. The quote right of OpenAPI is not exactly the same as that of APP. Some quotation cards are only applicable to the APP side (e.g., OpenAPI quotation cards for US stocks need to be purchased separately). Please confirm that the card you purchased is applicable to OpenD first. We have listed all the quotation cards applicable to OpenAPI in the section Authorities and Limitations. Please click here. 

2. After activating the quotation card, your quote right will be effective immediately. Please check after restarting OpenD. 

# Q13：How to Get Real-time Quotes Through Subscription Interface?

The First Stop：Subscription 

Pass the code of underlying security and data type to Subscription Interface to finish subscribing. 

Subscription interface supports requesting real-time quote, real-time order book, real-time tick-by-tick, real-time Time Frame, real-time candlesticks and real-time broker queue. After a successful subscription, OpenD will continuously receive real-time data from Futo Server. 

Attention: The subscription quota is allocated by your total capital, trading amount and trading volume. Please refer to Subscription Quota & Historical Candlestick Quota for details. If your subscription quota is not enough, please check if there is any useless subscriptions in the quota. Unsubscribe to release the subscription quota in time. 

The Second Step：Obtain Data 

We provide two methods to obtain subscribed data from OpenD: 

# Methos 1: Real-time data Callback

Set corresponding callback functions to process the pushed data asyncronously. 

After the callback function is set, OpenD will immediately push the received real-time data to the callback function of the script for processing. 

If the underlying security is very active, you may get a large amount of pushed data with high frequency. If you want to slower the push frequency of OpenD, we recommand you to config push frequency( qot_push_frequency ) in OpenD Startup Parameter 

The interfaces involved in mode 1 include: Real-time Quote Callback, Real-time Order Book Callback, Real-time Candlestick Callback, Real-time Time Frame Callback, Real-time Tick-by-Tick Callback, Real-time Broker Queue Callback. 

# Method 2: Get Real-time Data

Through the access to real-time data interface, you can use scripts to get the latest data received by OpenD. This approach is more flexible, and scripts do not need to deal with massive pushes. As long as OpenD continues to receive push from servers, the script can obtain the data on demand. 

As the data is taken from the pushed data received by OpenD, there is no frequency limit for this type of interface. 

The interfaces involved in mode 1 include: Get Real-time Quote of Securities, Get Real-time Order Book, Get Real-time Candlestick, Get Real-time Time Frame Data, Get Real-time Tickby-Tick, Get Real-time Broker Queue. 

# Q14：What time period corresponds to each market state？

A: 

<table><tr><td>Market</td><td>Security Type</td><td>Market State</td><td>Time Period (Local time)</td></tr><tr><td rowspan="2">HK Market</td><td rowspan="2">Securities (including stocks, ETFs,</td><td>* NONE: No trading</td><td>CST 08:55 - 09:00</td></tr><tr><td>* ACTION: Pre-market trading</td><td>CST 09:00 - 09:20</td></tr></table>

<table><tr><td rowspan="6">warrants, CBBCs, Inline Warrants)</td><td>* WAITING_OPEN: Waiting for opening</td><td>CST 09:20 - 09:30</td></tr><tr><td>* MORNING: Morning session</td><td>CST 09:30 - 12:00</td></tr><tr><td>* REST: Lunch break</td><td>CST 12:00 - 13:00</td></tr><tr><td>* AFTERNOON: Afternoon session</td><td>CST 13:00 - 16:00</td></tr><tr><td>* HK_CAS: After-hours bidding for HK stocks (The market state corresponding to the addition of CAS mechanism to the Hong Kong stock market)</td><td>CST 16:00 - 16:08</td></tr><tr><td>* CLOSED: Market closed</td><td>CST 16:08 - 08:55 (T+1)</td></tr><tr><td rowspan="5">Options, Futures (Day Market only)</td><td>* NONE: Waiting for options opening</td><td>CST 08:55 - 09:30</td></tr><tr><td>* MORNING: Morning session</td><td>CST 09:30 - 12:00</td></tr><tr><td>* REST: Lunch break</td><td>CST 12:00 - 13:00</td></tr><tr><td>* AFTERNOON: Afternoon session</td><td>CST 13:00 - 16:00</td></tr><tr><td>* CLOSED: Market closed</td><td>CST 16:00 - 08:55 (T+1)</td></tr><tr><td rowspan="4">Futures (Day and Night Market)</td><td>* FUTURE_DAY_WAIT_FOR_OPEN: Futures market wait for opening</td><td rowspan="4">Different trading time for different species</td></tr><tr><td>* NIGHT_OPEN: Night market trading hours</td></tr><tr><td>* NIGHT_END: Night market closed</td></tr><tr><td>* FUTURE_DAY_WAIT_FOR_OPEN: Futures market wait for opening</td></tr></table>

<table><tr><td></td><td></td><td>* FUTURE_DAY_OPEN: Day market trading hours</td><td rowspan="2"></td></tr><tr><td></td><td></td><td>* FUTURE_DAY_CLOSE: Day market closed</td></tr><tr><td rowspan="13">US Market</td><td rowspan="5">Securities (including stocks, ETFs)</td><td>* PREMARKET_BEGIN: Pre-market trading</td><td>EST 04:00 - 09:30</td></tr><tr><td>* AFTERNOON: Regular trading hours</td><td>EST 09:30 - 16:00</td></tr><tr><td>* AFTER_HOURS_BEGIN: After-hours trading</td><td>EST 16:00 - 20:00</td></tr><tr><td>* AFTER_HOURS_END: Market closed of U.S. stock market</td><td>EST 20:00 - 04:00 (T+1)</td></tr><tr><td>* OVERNIGHT: Overnight trading session of U.S. stock market</td><td>EST 20:00 - 04:00 (T+1)</td></tr><tr><td rowspan="6">Options</td><td>* NONE: Waiting for options opening</td><td rowspan="6">Different trading time for different species</td></tr><tr><td>* REST: Lunch break</td></tr><tr><td>* AFTERNOON: Regular trading hours</td></tr><tr><td>* TRADE_AT LAST: Late trading hours</td></tr><tr><td>* NIGHT: Night market trading hours</td></tr><tr><td>* CLOSED: Market closed</td></tr><tr><td rowspan="2">Futures</td><td>* NONE: Waiting for U.S. futures opening</td><td rowspan="2">Different trading time for different species</td></tr><tr><td>* FUTURE_OPEN: Trading hours of U.S. futures</td></tr><tr><td rowspan="3"></td><td rowspan="3"></td><td>* FUTURE_BREAK: Break of U.S. futures</td><td rowspan="3"></td></tr><tr><td>* FTRUE_BREAK_OVER: Trading hours of U.S. futures after break</td></tr><tr><td>* FUTURE_CLOSE: Market closed of U.S. futures</td></tr><tr><td rowspan="7">A-share Market</td><td rowspan="7">Securities (including stocks, ETFs)</td><td>* NONE: No trading</td><td>CST 08:55 - 09:15</td></tr><tr><td>* Action: Pre-market trading</td><td>CST 09:15 - 09:25</td></tr><tr><td>* WAITING_OPEN: Waiting for opening</td><td>CST 09:25 - 09:30</td></tr><tr><td>* MORNING: Morning session</td><td>CST 09:30 - 11:30</td></tr><tr><td>* REST: Lunch break</td><td>CST 11:30 - 13:00</td></tr><tr><td>* AFTERNOON: Afternoon session</td><td>CST 13:00 - 15:00</td></tr><tr><td>* CLOSED: Market closed</td><td>CST 15:00 - 08:55 (T+1)</td></tr><tr><td rowspan="5">Singapore Market</td><td rowspan="5">Futures</td><td>* FUTURE_DAY_WAIT_FOR_OPEN: Futures market wait for opening</td><td rowspan="5">Different trading time for different species</td></tr><tr><td>* NIGHT_OPEN: Night market trading hours</td></tr><tr><td>* NIGHT_END: Night market closed</td></tr><tr><td>* FUTURE_DAY_OPEN: Day market trading hours</td></tr><tr><td>* FUTURE_DAY_CLOSE: Day market closed</td></tr><tr><td rowspan="5">Japanese Market</td><td rowspan="5">Futures</td><td>* FUTURE_DAY_WAIT_FOR_OPEN: Futures market wait for opening</td><td>JST 16:25 (T-1) - 16:30 (T-1)</td></tr><tr><td>* NIGHT_OPEN: Night market trading hours</td><td>JST 16:30 (T-1) - 05:30</td></tr><tr><td>* NIGHT_END: Night market closed</td><td>JST 05:30 - 08:45</td></tr><tr><td>* FUTURE_DAY_OPEN: Day market trading hours</td><td>JST 08:45 - 15:15</td></tr><tr><td>* FUTURE_DAY_CLOSE: Day market closed</td><td>JST 15:15 - 16:25</td></tr></table>


* CST, EST, JST represent China time, US Eastern time, and Japan time respectively. 


# Q15：Parameter format of stock code.

A： 

For users with different programming languages, parameter format of stock code is different. 

0 Python users 

Format of stock code: market.code . 

For example: Tencent. Parameter code should be passed in 'HK.00700'. 

Non-Python users 

For stock structure, refer to Security. 

For example: Tencent. Parameter market should be passed in QotMarket_HK_Security, parameter code should be passed in '00700'. 

Quick inquiries. View the code and market through APP: Quotes $>$ Watchlists $>$ All. 

For Quote Market, refer to here. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/c9f0633d2dec90f036f94455f9f11f2f19eac68e202309a6079bda895ef1bf0d.jpg)


# Q16：Stock Price Adjustment

A： 

# Overview

Price adjustment refers to adjusting stock price and trading volume after corporate actions, so that the price chart can better represent actual price moves and trading volume. 

Corporate actions such as stock split, reverse stock split, bonus issue, rights issue, allotment, secondary offering, and dividend payment can affect the stock price. Price adjustment 

eliminates the impact of corporate actions on stock price and trading volume, and maintains the continuity of the stock price moves. 

# Tips

The information on this page is mainly intended for the China A-share market. 

# Glossary

Corporate action: Actions on equity and stock conducted by a listed company that affect the company's stock price and number of shares. 

Default adjustment: Keep the current stock price unchanged, and use it as the benchmark to re-calculate all previous stock prices. 

Cumulative adjustment: Keep the stock price before the earliest corporate action unchanged, and use it as the benchmark to re-calculate all future stock prices. 

Price adjustment factor: The ratio used to re-calculate the adjusted and cumulative stock prices and number of shares after a corporate action. There are two types of price adjustment factors: the default adjustment factor for calculating the adjusted price and the cumulative adjustment factor for calculating the cumulative price. 

Ex-div and pay date: The next trading day of the registration date. The stock exchange must calculate the adjusted stock price before market open on the ex-and-pay date. It is also the date on which dividends are distributed to shareholders and changes in the number of shares take place. 

# Price Adjustment Methods

There are two price adjustment methods: two-step method and continuous multiplication. OpenAPI uses different adjustment methods for different markets. 

Two-step method: The stock price is adjusted based on corporate actions; there are 2 factors in this method: factor A for cash dividends and factor B for all other corporate actions. 

Continuous multiplication: The stock price is adjusted the continuously multiplying the adjustment factors. This method can be seen as a special case of two-step method with factor B as 0. 

# Tips:

OpenAPI uses continuous multiplication for calculating the adjusted price of US stocks, with the price adjustment factor B set to 0. 

OpenAPI uses two-step method for stocks other than US stocks (China A-shares, Hong Kong stocks, Singapore stocks, etc.) and for calculating the cumulative price of US stocks. 

# Calculation Formulae

# Single Adjustment

. Default adjustment: 

Adjusted price $=$ Actual price $\times$ Default adjustment factor A $^ +$ Default adjustment factor B 

. Cumulative adjustment: 

Cumulative price $=$ Actual price $\times$ Cumulative adjustment factor A + Cumulative adjustment factor B 

# Multiple Price Adjustments

Default adjustment: In chronological order, select the adjustment factors later than the adjustment date, and first use earlier adjustment factors for calculation. Take a double adjustment as an example: 

$$
P r i c e _ {n} ^ {\text {a d j u s t e d}} = \left(P r i c e _ {n} * F a c t o r A _ {n + 1} ^ {\text {a d j u s t e d}} + F a c t o r B _ {n + 1} ^ {\text {a d j u s t e d}}\right) * F a c t o r A _ {n + 2} ^ {\text {a d j u s t e d}} + F a c t o r B _ {n + 2} ^ {\text {a d j u s t e d}}
$$

$P r i c e _ { n } ^ { a d j u s t e d }$ 

Pricen:Actual price of the day 

$F a c t o r A _ { n + 2 } ^ { a d j u s t e d }$ Andjusted：Default adjustment factor A of the next two days 

$F a c t o r B _ { n + 2 } ^ { a d j u s t e d }$ 

Cumulative adjustment: In reverse chronological order, select the adjustment factors earlier than or on the calculation date, and first use later adjustment factors for calculation. Take a double adjustment as an example: 

$$
P r i c e _ {n} ^ {\text {c u m u l a t i v e}} = \left(P r i c e _ {n} * F a c t o r A _ {n} ^ {\text {c u m u l a t i v e}} + F a c t o r B _ {n} ^ {\text {b a c k w a r d}}\right) * F a c t o r A _ {n - 1} ^ {\text {c u m u l a t i v e}} + F a c t o r B _ {n - 1} ^ {\text {c u m u l a t i v e}}
$$

$P r i c e _ { n } ^ { c u m u l a t i v e }$ 

Pricen:Actual price of the day 

# Examples

Example of a single adjustment 

Take the stock of Muyuan Foods as an example: 

. Screening weighting factors are as follows: 

<table><tr><td>Ex-Div and 
Pay Date</td><td>Stock 
Symbol</td><td>Corporate 
Action Details</td><td>Default 
Adjustment 
Factor A</td><td>Default 
Adjustment 
Factor B</td></tr><tr><td>06/03/2021</td><td>SZ.002714</td><td>10-share dividends: 4 shares and ¥14.61 (tax included)</td><td>0.71429</td><td>-1.04357</td></tr></table>

. Data on actual price: 

<table><tr><td>Date</td><td>Stock Symbol</td><td>Actual Closing Price</td></tr><tr><td>06/02/2021</td><td>SZ.002714</td><td>93.11</td></tr><tr><td>06/03/2021</td><td>SZ.002714</td><td>66.25</td></tr></table>

. Data on adjusted prices: 

<table><tr><td>Date</td><td>Stock Symbol</td><td>Adjusted Closing Price</td></tr><tr><td>06/02/2021</td><td>SZ.002714</td><td>65.4639719</td></tr><tr><td>06/03/2021</td><td>SZ.002714</td><td>66.25</td></tr></table>

. Method for calculating adjusted prices: 

Muyuan Foods conducted a stock split and paid cash dividends on 2021/06/03 (4 shares and $\yen 14.67$ for every 10 shares owned), and here is how to calculate the adjusted closing price on 06/02/2021: Adjusted price (65.4639719 ) $=$ Actual price (93.11) $\times$ Default adjustment factor A (0.71429) $^ +$ Default adjustment factor B (-1.04357) 


Actual Price


<table><tr><td>Date</td><td>Stock Symbol</td><td>Actual Closing Price</td><td colspan="5">Adjusted Price</td></tr><tr><td>06/02/2021</td><td>SZ.002714</td><td>93.11</td><td rowspan="3" colspan="3">93.11 × 0.71429 - 1.04357 = 65.4639719</td><td>Date</td><td>Stock Symbol Adjusted Closing Price</td></tr><tr><td>06/03/2021</td><td>SZ.002714</td><td>66.25</td><td>06/02/2021</td><td>SZ.002714 65.4639719</td></tr><tr><td></td><td></td><td></td><td>06/03/2021</td><td>SZ.002714 66.25</td></tr><tr><td colspan="8">Adjustment Factors</td></tr><tr><td>Ex-Div and Pay Date</td><td>Stock Symbol</td><td>Corporate Action Details</td><td>Default Adjustment A</td><td>Default Adjustment B</td><td>Default Adjustment B</td><td></td><td></td></tr><tr><td>06/03/2021</td><td>SZ.002714</td><td>10-share dividends: 4 shares and ¥14.61 (tax included)</td><td>0.71429</td><td>-1.04357</td><td></td><td></td><td></td></tr></table>

# Example of multiple cumulative adjustment

Following on the previous example, here is how to calculate the cumulative price of Muyuan Foods on 06/02/2021: 

. Adjustment factors are as follows: 

<table><tr><td>Ex-Date</td><td>Stock 
Symbol</td><td>Corporate Action 
Details</td><td>Cumulative 
Factor A</td><td>Cumulative 
Factor B</td></tr><tr><td>07/04/2014</td><td>SZ.002714</td><td>10-share dividends: 
¥2.34 (tax included)</td><td>1</td><td>0.234</td></tr><tr><td>06/10/2015</td><td>SZ.002714</td><td>10-share dividends: 
10 shares and ¥0.61 
tax included)</td><td>2</td><td>0.061</td></tr><tr><td>07/08/2016</td><td>SZ.002714</td><td>10-share dividends: 
10 shares and ¥3.53 
tax included) (tax 
included)</td><td>2</td><td>0.353</td></tr><tr><td>07/11/2017</td><td>SZ.002714</td><td>10-share dividends: 8 
shares and ¥6.9 (tax 
included)</td><td>1.8</td><td>0.69</td></tr><tr><td>07/03/2018</td><td>SZ.002714</td><td>10-share dividends: 
¥6.91 (tax included)</td><td>1</td><td>0.691</td></tr><tr><td>07/04/2019</td><td>SZ.002714</td><td>10-share dividends: 
¥0.5 (tax included)</td><td>1</td><td>0.05</td></tr><tr><td>06/04/2020</td><td>SZ.002714</td><td>10-share dividends: 7 shares and ¥5.5 (tax included)</td><td>1.7</td><td>0.55</td></tr></table>

? Data on actual prices: 

<table><tr><td>Date</td><td>Stock Symbol</td><td>Actual Price</td></tr><tr><td>06/02/2021</td><td>SZ.002714</td><td>93.11</td></tr></table>

. Data on cumulative prices: 

<table><tr><td>Date</td><td>Stock Symbol</td><td>Cumulative Price</td></tr><tr><td>06/02/2021</td><td>SZ.002714</td><td>1152.7226</td></tr></table>

. Method for calculating cumulative prices: 

To calculate the cumulative price of Muyuan Foods on June 2, 2021, all the corporate actions by June 2, 2021 need to be taken into account. The detailed calculations are as follows: 

# Actual Price

<table><tr><td>Date</td><td>Stock Symbol</td><td colspan="4">Actual Price</td></tr><tr><td rowspan="3">02/06/2021</td><td rowspan="3">SZ.002714</td><td rowspan="3">93.11</td><td colspan="3">Cumulative Price</td></tr><tr><td>Date</td><td>Stock Symbol</td><td>Cumulative Price</td></tr><tr><td>02/06/2021</td><td>SZ.002714</td><td>1152.7226</td></tr><tr><td colspan="6">Adjustment Factors</td></tr><tr><td>Ex-Date</td><td>Stock Symbol</td><td>Corporate Action Details</td><td>Cumulative A</td><td>Cumulative B</td><td>Cumulative Factor</td></tr><tr><td>07/04/2014</td><td>SZ.002714</td><td>10-share dividends: ¥ 2.34 (tax included)</td><td>1</td><td>0.234</td><td></td></tr><tr><td>06/10/2015</td><td>SZ.002714</td><td>10-share dividends: 10 shares and ¥ 0.61 tax included)</td><td>2</td><td>0.061</td><td></td></tr><tr><td>07/08/2016</td><td>SZ.002714</td><td>10-share dividends: 10 shares and ¥ 3.53 tax included) (tax included)</td><td>2</td><td>0.353</td><td></td></tr><tr><td>07/11/2017</td><td>SZ.002714</td><td>10-share dividends: 8 shares and ¥ 6.9 (tax included)</td><td>1.8</td><td>0.69</td><td></td></tr><tr><td>07/03/2018</td><td>SZ.002714</td><td>10-share dividends: ¥ 6.91 (tax included)</td><td>1</td><td>0.691</td><td></td></tr><tr><td>07/04/2019</td><td>SZ.002714</td><td>10-share dividends: ¥ 0.5 (tax included)</td><td>1</td><td>0.05</td><td></td></tr><tr><td>06/04/2020</td><td>SZ.002714</td><td>10-share dividends: 7 shares and ¥ 5.5 (tax included)</td><td>1.7</td><td>0.55</td><td></td></tr></table>

# Transaction related

# Q1: How to use paper trading?

A: 

# Overview

Paper trading is a simulation that allows you to practice trading without the risk of using real money. 

# Trading time

Paper trading only supports trading during regular trading hours, and does not support trading outside regular trading hours, US market premarket and after-hours, HK market and China A-shares market Opening and Closing Auction. For details, please click Rules of paper trading . 

# Categories supported

For categories that OpenAPI supports by paper trading, please click here. 

# Unlock Trade

Different from live trading, you do not need to unlock the account to place orders or modify or cancel orders when using paper trading. 

# Orders

1. Order Types: limit order and market order. 

2. Modify Order Operation: Paper trading does not support enabling, disabling, and deleting the order, but supports modifying and canceling the order. 

3. Deals: Paper trading does not support deals related operations, including Get today's deals, Get historical deals, and Respond to the transaction push. 

4. Valid Period: Paper trading only supports good for day order when setting valid period. 

5. Short Selling: Options and futures support short selling. Only US stocks support short selling. 

# Platform

1. Mobile clients: Me — Paper Trading. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/732588bd8d96a53e6ee7c404578c3c7b1c5dcad9adea011ac9c3cb9b38098d97.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/2c3831940d204929970562f493bc120f62595d1d4c4b85d5c46ee94e9f8bfe7c.jpg)


# 2. Desktop clients: Left side tab Paper .

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/4f2bf02f54e6935f1d1491db8ce6e52b2100fec55d8550470c504aa4ad82b56f.jpg)


# 3. Web clients: Paper Trading Website .

4. OpenAPI: When calling the interface, set the parameter trading environment to the simulated environment. Click How to use paper trading through OpenAPI for detail. 

Tips 

The four platforms shown above use the same paper trading accounts. 

# How to use paper trading through OpenAPI?

# Create Connection

Firstly, create the corresponding connection. When the underlyings are stocks or options, please use OpenSecTradeContext . When the underlyings are futures, please use OpenFutureTradeContext 

# Get the List of Trading Accounts

Use the interface Get the List of Trading Accounts to view trading accounts (including paper trading accounts and live trading accounts). Take Python as an example: When the returned parameter trd_env is SIMULATE , it means the corresponding account is a paper trading account. 

# Example：Stocks and Options

```python
from futu import *
trdctx = OpenSecTradeContext.filter(trdmarket=TrdMarket.HK, host='127.0.0.1', port=11111, security_firm=SecurityFirm.FUTUSECURITIES)
# trdctx = OpenFutureTradeContext(host='127.0.0.1', port=11111, is Encrypt=None, security_firm=SecurityFirm.FUTUSECURITIES)
ret, data = trdctx.get_acc_list()
if ret == RET_OK:
    print(data)
    print(data['acc_id']) # get the first account id
    print(data['acc_id'].values.tolist()) # convert to list format
else:
    print('get_acc_list error: ', data)
trdctx.close() 
```

# Output

```c
1 acc_id trd_env acc_type card_num security_firm \ py 2 REAL MARGIN 1001318721909873 FUTUSECURITIES 3 1 9053218 SIMULATE CASH N/A N/A 4 2 9048221 SIMULATE MARGIN N/A N/A 5 sim_acc_type trdmarket_auth 6 0 N/A [HK, US, HKCC] 7 1 STOCK [HK] 8 2 OPTION [HK] 
```

# Tips

In paper trading, stock accounts and options accounts are distinguished. Stock accounts can only trade stocks, and options accounts can only trade options; take Python as an example: sim_acc_type in the returned field is STOCK , which means stock account; OPTION means option account. 

# Example: Futures

```python
from futu import *
# trdCtx = OpenSecTradeContext.filter_trdmarket = TrdMarket.HK, host = '127.0.0.1', port = 11111, security_firm = SecurityFirm.FUTUSECUB
trdCtx = OpenFutureTradeContext(host = '127.0.0.1', port = 11111, is Encrypt = None, security_firm = SecurityFirm.FUTUSECURITIES)
ret, data = trdCtx.get_acc_list()
if ret == RET_OK:
    print(data)
    print(data['acc_id'].0) # get the first account id
    print(data['acc_id'].values.tolist()) # convert to list format 
```

```python
9 else:   
10 print('get_acc_list error:'，data)   
11 trdctx.close() 
```


Output


```txt
py   
1 acc_id trd_env acc_type card_num security_firm sim_acc_type \   
2 0 9497808 SIMULATE MARGIN N/A N/A FUTURES   
3 1 9497809 SIMULATE MARGIN N/A N/A FUTURES   
4 2 9497810 SIMULATE MARGIN N/A N/A FUTURES   
5 3 9497811 SIMULATE MARGIN N/A N/A FUTURES   
6   
7 trdmarket_auth   
8 0 [FUTURES_SIMULATE_HK]   
9 1 [FUTURES_SIMULATE_US]   
10 2 [FUTURES_SIMULATE_SG]   
11 3 [FUTURES_SIMULATE_JP] 
```


Place Orders


When using the Interface Place Orders, set the trading environment to the simulated environment. Take Python as an example: trd_env TrdEnv.SIMULATE . 


Example


```python
1 from futu import *
2 trdctx = OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host='127.0.0.1', port=11111, security_firm=SecurityFirm.FUTUSECUR
3 ret, data = trdctx.place_order(price=510.0, qty=100, code='HK.00700', trdSide=TrdSide.BUY, trd_env=TrdEnv.SIMULATE)
4 if ret == RET_OK:
5 print(data)
6 else:
7 print('place_order error: ', data)
8 trdctx.close()
```
`` 
```


Output


```txt
1 code stock_name trdSide order_type order_status order_id qty price create_time updated_time dealt_qty 2 HK.00700 Tencent BUY NORMAL SUBMITTING 4642000476506964749 100.0 510.0 2021-10-09 11:34:54 2021-10-09 
```


Modify or Cancel Orders


When using the Interface Modify or Cancel Orders, set the trading environment to the simulated environment. Take Python as an example: trd_env $=$ TrdEnv.SIMULATE 


Example


```python
from futu import *
trdctx = OpenSecTradeContext.filter_trdmarket=TrdMarket.HK, host='127.0.0.1', port=11111, security_firm=SecurityFirm.FUTUSECUR
order_id = "4642000476506964749"
ret, data = trdctxmodify_order(ModifyOrderOp.CANCEL, order_id, 0, 0, trd_env=TrdEnv.SIMULATE)
if ret == RET_OK:
    print(data)
else:
    print('modify_order error: ', data)
trdctx.close() 
```

Output 

<table><tr><td>1</td><td>trd_env</td><td>order_id</td><td>py</td></tr><tr><td>2</td><td>0</td><td>SIMULATE 4642000476506964749</td><td></td></tr></table>

# Get Historical Orders

When using the Interface Get Historical Orders, set the trading environment to the simulated environment. Take Python as an example: 

```txt
trd_env = TrdEnv.SIMULATE. 
```

Example 

```markdown
1 from futu import *
2 trdctx = OpenSecTradeContext.filter(trdmarket=TrdMarket.HK, host='127.0.0.1', port=11111, security_firm=SecurityFirm.FUTUSECUR
3 ret, data = trdctx_history_order_list_query(trd_env=TrdEnv.SIMULATE)
4 if ret == RET_OK:
5 print(data)
6 else:
7 print('history_order_list_query error: ', data)
8 trdctx.close()
``` 
```

Output 

<table><tr><td>1</td><td>code stock_name</td><td>trd_side</td><td>order_type</td><td>order_status</td><td>order_id</td><td>qty</td><td>price</td><td>create_time</td><td>updated_time</td><td>dealt_qty</td><td>py</td></tr><tr><td>2</td><td>0</td><td>HK.00700</td><td>Tencent</td><td>BUY</td><td>ABSOLUTE_LIMIT</td><td>CANCELED_ALL</td><td>4642000476506964749</td><td>100.0</td><td>510.0</td><td>2021-10-09</td><td>11:34:54</td></tr></table>

# How to reset the paper trading account?

Currently, OpenAPI does not support resetting the paper trading account. You can use the reset card on the mobile clients. After the reset, net assets would be restored to the initial value and the historical orders would be emptied. 

Specific process 

Modify clients: Me — Paper Trading — My Icon — My Card — Reset Card 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/1104b4216619009f790cf176ce3d396d095b0c64ed74c630cbc54bf9cf4e998c.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/bb9013726d94f111c8513eda4e9fb9b9648231e70d90379326283d3dd85af94c.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/540c1cfb5efba4753a7121dbb8286d8d69aa4da1ad1dbf520d1c96b468db432b.jpg)


# How to reset the paper trading account?

Currently, OpenAPI does not support resetting the paper trading account. You can use the reset card on the mobile clients. After the reset, net assets would be restored to the initial value and the historical orders would be emptied. 

Specific process 

Modify clients: Me — Paper Trading — My Icon — My Card — Reset Card 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/ab1cb8ad99ccf7de4c82e13ad0e15e43a7b2bbaa220bfcca42a2c05cdebe2929.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/046bf7dbd16711febd7eca01554d44d45335fefc4488171c4d7f995a259d0bfa.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/73f401ed9838ba81ee11748bd4179b6f793799c05a719b84eafac2dba3f1e601.jpg)


# Q2: If support A-share trading or not?

A: Paper trading supports A-share trading. However, real trade can only be used to trade some A-shares through A-shares connect. For details, please refer to List of HKCC . 

# Q3: Trading directions supported by each market

A: Except for futures, other stocks only support the two trading directions of BUY and SELL. In the case of a short position, SELL is passed in, and the direction of the resulting order is short selling. 

# Q4: Order types supported in each market in real environment

A: 

<table><tr><td>Market</td><td>Variety</td><td>Limit Orders</td><td>Market Orders</td><td>At-auction Limit Orders</td><td>At-auction Market Orders</td><td>Absolute Limit Orders</td><td>Special Limit Orders</td><td>AON Special Limit Orders</td><td>Stop Orders</td><td>Stop Limit Orders</td><td>Market if Touched Orders</td><td>Limit if Touched Orders</td></tr><tr><td rowspan="2">HK</td><td>Securities (including stocks, ETFs, warrants, CBBCs, Inline Warrants)</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Options</td><td>✓</td><td>X</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>X</td><td>✓</td><td>X</td><td>✓</td></tr><tr><td></td><td>Futures</td><td>✓</td><td>✓</td><td>-</td><td>✓</td><td>-</td><td>-</td><td>-</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td rowspan="3">US</td><td>Securities (including stocks, ETFs)</td><td>✓</td><td>✓</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Options</td><td>✓</td><td>✓</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Futures</td><td>✓</td><td>✓</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>HKCC</td><td>Securities (including stocks, ETFs)</td><td>✓</td><td>X</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>X</td><td>✓</td><td>X</td><td>✓</td></tr><tr><td>Singapore</td><td>Futures</td><td>✓</td><td>✓</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Japanese</td><td>Futures</td><td>✓</td><td>✓</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr></table>

# Q5: Order operations supported by each market

A: 

HK stocks support order modification, cancellation, entry into force, invalidation, and deletion 

US stocks only support order modification and cancellation 

HKCC only supports cancellation of orders 

Futures supports order modification, cancellation, and deletion 

# Q6: How to use OpenD startup parameter future_trade_api_time_zone?

A: Since the types of futures supported for trading account are distributed in multiple exchanges around the world, and the time zones of the exchanges are different, the time display of the futures trading API has become a problem. The future_trade_api_time_zone parameter has been added to the OpenD startup parameters, allowing futures traders in different regions of the world to flexibly specify the time zone. The default time zone is UTC+8. If you are more accustomed to Eastern Time, you only need to configure this parameter to UTC-5. 

# Tips

This parameter is only valid for futures trading interface objects. The time zone of HK stock trading, US stock trading, and HKCC trading interface objects is still displayed in accordance with the time zone of the exchange. 

The interfaces affected by this parameter include: responding to order push callbacks, responding to transaction push callbacks, querying today's orders, querying historical orders, querying current transactions, querying historical transactions, and placing orders. 

# Q7: Can I see the order placed through OpenAPI, in APP?

A：Yes, you can. 

After the order is successfully placed through OpenAPI, you can view today's orders, order status change in the trade page of APP, and you can also receive Order Notice in the APP. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/0e205cf6d2eaf3b8e8fba87f9652695795f0fb12ed038d6e28c8e1cb621f37b6.jpg)


iPhone/iPad Download 

Android Download 

Mac Download 

Windows Download 

Futu API 

Ver.2.19.1250 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/d881b0f5de1fe317d7db5b7e07edd752051d001171a3b352ea1f08d7b2ea78a0.jpg)


1.【新增】订阅接口支持美股盘前盘后时段的逐笔数据

# Q8: Which trading targets support Off-Market order?

A：All orders can only be filled during the market opening period. 

Orders made outside market hours and extended hours trading are queued and fulfilled either at or near the beginning of extended hours trading or at or near the market open, according to your instructions. These orders may be named as off market orders or overnight order. 

OpenAPI supports Off-Market order for a part of trading targets (APP supports much more trading targets' Off-Market order), as follows: 

<table><tr><td rowspan="2">Market</td><td rowspan="2">Contracts</td><td rowspan="2">Paper Trading</td><td colspan="7">Live Trading</td></tr><tr><td>FUTU HK</td><td>Moomoo Financial Inc.</td><td>Moomoo Financial Singapore Pte. Ltd.</td><td>Moomoo AU</td><td>Moomoo MY</td><td>Moomoo CA</td><td>Moomoo JP</td></tr><tr><td rowspan="3">HK Market</td><td>Securities (including stocks, ETFs, warrants, CBBCs, Inline Warrants)</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>X</td><td>X</td></tr><tr><td>Options</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Futures</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td rowspan="3">US Market</td><td>Securities (including stocks, ETFs)</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Options</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>Futures</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>✓</td><td>X</td><td>X</td></tr><tr><td rowspan="2">A-share Market</td><td>HKCC stocks</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Non-HKCC stocks</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Singapore Market</td><td>Futures</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td rowspan="2">Japanese Market</td><td>Securities (including stocks, ETFs, REITS)</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Futures</td><td>✓</td><td>✓</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Australian Market</td><td>Securities (including stocks, ETFs)</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr><tr><td>Canadian Market</td><td>Securities</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td><td>X</td></tr></table>

# Tip

✓：support Off-Market order 

X：do not support Off-Market order（or non-tradable） 

# Q9: For each order type，mandatory parameters of PlaceOrder and broker limits for the single order.


A1: Mandatory parameters of PlaceOrder.


<table><tr><td>Parameters</td><td>Limit Orders</td><td>Market Orders</td><td>At-auction Limit Orders</td><td>At-auction Market Orders</td><td>Absolute Limit Orders</td><td>Special Limit Orders</td><td>AON Special Limit Orders</td><td>Stop Orders</td><td>Stop Limit Orders</td><td>Market if Touched Orders</td><td>Limit if Touched Orders</td><td>Trailing Stop Orders</td></tr><tr><td>price</td><td>✓</td><td></td><td>✓</td><td></td><td>✓</td><td>✓</td><td>✓</td><td></td><td>✓</td><td></td><td>✓</td><td></td></tr><tr><td>qty</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>code</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>trdSide</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>order_type</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>trd_env</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>aux_price</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td></td></tr><tr><td>trail_type</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>✓</td></tr><tr><td>trail_value</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>✓</td></tr><tr><td>trail_spread</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></table>

Python users should note that, place_order does not set a default value for price. For the five types of orders mentioned above, you still need to pass in price, which can be any value. 

A2: The broker sets limits on shares or amounts for single orders of various trading products. Exceeding these limits may result in order failures. See the table below for details. 

<table><tr><td>Broker</td><td>Product</td><td>Quantity Limit Per Order</td><td>Amount Limit Per Order</td></tr><tr><td rowspan="3">FUTU HK</td><td>China A-Shares</td><td>1,000,000 Shares</td><td>¥ 5,000,000</td></tr><tr><td>US Stocks</td><td>500,000 Shares</td><td>$5,000,000</td></tr><tr><td>Hong Kong Stock Futures or Options</td><td>3,000 Contracts</td><td>Unlimited</td></tr><tr><td>moomoo US</td><td>US Stocks</td><td>500,000 Shares</td><td>$10,000,000</td></tr><tr><td>moomoo SG</td><td>US Stocks</td><td>500,000 Shares</td><td>$5,000,000</td></tr><tr><td>moomoo AU</td><td>US Stocks</td><td>Unlimited</td><td>Unlimited</td></tr></table>

Q10: For each order type, when modifying the order, mandatory parameters of ModifyOrder as follows. 

<table><tr><td>Parameters</td><td>Limit Orders</td><td>Market Orders</td><td>At-auction Limit Orders</td><td>At-auction Market Orders</td><td>Absolute Limit Orders</td><td>Special Limit Orders</td><td>AON Special Limit Orders</td><td>Stop Orders</td><td>Stop Limit Orders</td><td>Market if Touched Orders</td><td>Limit if Touched Orders</td><td>Trailif Stop Orders</td></tr><tr><td>modify_order_op</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>order_id</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>price</td><td>✓</td><td></td><td>✓</td><td></td><td>✓</td><td>✓</td><td>✓</td><td></td><td>✓</td><td></td><td>✓</td><td></td></tr><tr><td>qty</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>trd_env</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr><tr><td>aux_price</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td></td></tr><tr><td>trail_type</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>✓</td></tr><tr><td>trail_value</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>✓</td></tr><tr><td>trail_spread</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></table>

Python users should note that, modify_order does not set a default value for price. For the five types of orders mentioned above, you still need to pass in price, which can be any value. 

Q11: The Trade API returns "The current securities account has not yet agreed to the disclaimer."? 

A: 

Click the link below to confirm the agreement, and restart OpenD to use trading functions normally. 

<table><tr><td>Securities Firm</td><td>Aggrement Link</td></tr><tr><td>FUTU HK</td><td>Click here ☐</td></tr><tr><td>Moomoo US</td><td>Click here ☐</td></tr><tr><td>Moomoo SG</td><td>Click here ☐</td></tr><tr><td>Moomoo AU</td><td>Click here ☐</td></tr><tr><td>Moomoo CA</td><td>Click here ☐</td></tr><tr><td>Moomoo MY</td><td>Click here ☐</td></tr><tr><td>Moomoo JP</td><td>Click here ☐</td></tr></table>

# Q12: Pattern Day Trader (PDT)

# Overview

When clients use Moomoo US accounts for intraday trading, they are subject to regulations by the US Financial Industry Regulatory Authority (FINRA). This is a regulatory requirement for US brokers and has nothing to do with the market to which a stock being traded belongs. The trading accounts of brokers in other countries or regions, such as Futu HK and Moomoo SG accounts, are not subject to this restriction. If a client conducts over 3 day trades in any 5 consecutive trading days, the client will be labelled as a pattern day trader (PDT). 

For more details, refer to Help Center - Day Trade Rules . 

Day Trading Flowchart 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/52fcfc82e0a3e230768736b7af8737dbd31c0fc79009a9e622e155abf37a4c37.jpg)


How to turn off "Pattern Day Trade Protection", if I'm willing to be labelled as a PDT and do not want the quant trading program to be interrupted? 

A: 

To prevent you from being unintentionally labelled as a PDT, the server will automatically intercept your 4th day trade in any 5 consecutive trading days. If you are willing to be labelled as a PDT and do not want the server to intercept your trade, you can take the following step: Via Command Line OpenD, modify the value of the startup parameter "pdt_protection" to $" 0 "$ . 

```sgml
<!-- FUTU US 专用参数 -->
<!-- Specific parameters for FUTU US -->
--- 是否开启 防止被标记为日内交易者 的功能,0:否,1:是-->
<-- 开启功能后,我们会在您将要被标记 PDT 时阻止您的下单,但不确保您一定不被标记。若您被标记 PDT,当您的账户权益小于$25000时,您将无法开仓。-->
<-- Whether to turn on the Pattern Day Trade Protection,0:No,1:Yes -->
<-- When this parameter is set as 1, we will prevent you from placing orders which might mark you as a Pattern Day Trader(PDT). The Protection c
<pdt_protection1>/pdt_protection>
```

NOTE: You will not be able to establish new positions when you are labelled as a PDT and your account equity is below $\$ 25000$ . 

# How to turn off the Day-Trading Call Warning?

A: 

Once you are labelled as a PDT, you need to pay attention to the day trading buying power (DTBP) of your account. When the DTBP is insufficient, you will receive a DTCall. The server will intercept your order that exceeds the DTBP. If you still want to place the order and do not want the server to intercept it, you can take the following step: 

Via Command Line OpenD, modify the value of the startup parameter "dtcall_confirmation" to "0". 

<!--开启功能后，我们会在您即将开仓下单超出剩余日内交易购买力前阻止您的下单。提醒您当前开仓订单的市值大于您的剩余日内交易购买力，若您在今日平仓当前标的，

<dtcall_confirmation1:/dtcall_confirmation> 

NOTE: If the market value of a newly established position exceeds your remaining DTBP and you close the position in the same day, you will receive a DTCall, which can only be met by depositing funds. 

# How to check my DTBP?

A: 

Via Get Account Funds Interface, you can request values related to day trading, such as Day Trades Left, Beginning DTBP, Remaining DTBP, etc. 

# Q13: How to track the status of orders?

The two interfaces can be uesed to track the status of orders, after which have been placed. 

<table><tr><td>Trading Enviroment</td><td>Interfaces</td></tr><tr><td>Real</td><td>Orders Push Callback, Deals Push Callback</td></tr><tr><td>Simulate</td><td>Orders Push Callback</td></tr></table>

Note: Non-python users need to Subscribe to Transaction Push before using the above two interfaces. 

# Orders Push Callback:

Feedback changes of the entire order. The order push will be triggered when the following 8 fields change: 

Order status Order price , Order quantity , Deal quantity , Traget price Trailing type Trailing amount/ratio Specify spread 

Therefore, when you place, modify, cancel, enable, or disable the order, or when an advanced order is triggered or an order has transaction changes, it will cause orders push. You just need to call the Orders Push Callback to listen for these messages. 

# Deals Push Callback:

Feedback changes of a transaction. The order push will be triggered when the following field change: 

Deal status 

Fot example: Suppose a limit order of 900 shares is divided into 3 transactions before it is completely filled, with each transaction being 200, 300 and 400 shares. 

# Q14: Why does the order interface return “The minimum tick size for this product is xxx. Please enter an integer multiple of the minimum tick size before submitting”?

A: 

Different exchanges have different rules on order price spreads. If the price of a submitted order does not follow relevant rules, the order will be rejected. 

# Rules on Price Spread

Hong Kong Market 

Refer to the official HKEX Spread Table 

China A-Shares 

Stock price spread: 0.01 

US Market 

Stock Price Spreads: 

<table><tr><td>Price</td><td>Spread</td></tr><tr><td>Below $1</td><td>$0.0001</td></tr><tr><td>$1 or above</td><td>$0.01</td></tr></table>

Option Price Spreads: 

<table><tr><td>Price</td><td>Spread</td></tr><tr><td>$0.10 – $3.00</td><td>$0.01 or $0.05</td></tr><tr><td>$3.00+</td><td>$0.05 or $0.10</td></tr></table>

Futures Price Spreads: 

Different contracts have different price spreads, which can be obtained via the Price change step of Get Futures Contract Information interface. 

# How to ensure an order price meets spread rules?

Method 1: Valid order prices can be obtained via the Get Real-time Order Book interface, since the prices of orders on the order book must be valid. 

Method 2: Auto-adjust an order price to a valid value via the Price adjustment range parameter in the Place Orders interface. 

How it works: 

Suppose the Adjust Limit is set to 0.0015. A positive value means that OpenD will auto-adjust upward the price of a submitted order to a valid value within $+ 0 . 1 5 \%$ of the original price. 

Suppose the current market price of Tencent Holdings is 359.600, so the spread is 0.200 according to the HKEX Spread Table. Let’s say an order priced at 359.678 is submitted. In this case, the nearest upward valid price is 359.800, which means the order price only needs to be adjusted by $0 . 0 3 4 \%$ . The adjustment satisfies the Adjust Limit, so the final price of the submitted order is 359.800. 

If the actual adjustment exceeds the Adjust Limit, OpenD will fail to auto-adjust the price, and the order submission will still return the error prompt "The minimum tick size for this product is xxx. Please enter an integer multiple of the minimum tick size before submitting". 

# Q15: Why did it say "Insufficient Buying Power" when I place a market order with enough buying power in my account?

A: 

# Why it indicates insufficient buying power when you place a market order

For the sake of risk management, the system poses a higher buying power coefficient on market orders. With the same order parameters, a market order takes up more buying power than a limit order. 

Depending on different product types and market conditions, the risk management system dynamically adjusts the buying power coefficient of market orders. Therefore, when placing a market order, if you calculate the maximum buyable quantity using your maximum buying power, you are likely to get an inaccurate result. 

# How to get the correct buyable quantity

Instead of calculating it, you can obtain the correct buyable quantity through the [Query the Maximum Quantity that Can be Bought or Sold] (../trade/get-max-trd-qtys.html) API. 

# How to buy as much as possible

You can place a limit order at the BBO, instead of a market order. In particular, the BBO means the best bid (or Bid 1) in the case of a sell order, or the best ask (or Ask 1) for a buy order. 

# Q16: Why can't I see the API papper trading orders on the mobile app?

A: 

On all the mobile, desktop and website, the US stock paper trading account has been upgraded from the US Paper Trading Accounts to the US Paper Trading Margin Accounts. 

The OpenAPI has not yet been upgraded (planning phase). At present, only the old US Paper Trading Account is available for use. Please note that this old account cannot be displayed on other clients, so use it with caution. 

# Q17: Instructions for Using Trade API Parameters

# 1. What is the Transaction Object?

Under your user ID, there is generally a margin universal account with several sub-accounts (usually two, a univeral securities account and a universal futures accoun; also a universal forex account if needed). Some users or instituational clients may open multiple universal accounts with multiple brokers. 

Creating a transaction object is the process of initially screening sub-accounts. 

When calling get_acc_list using OpenSecTradeContext, only trading securities accounts will be returned. 

When calling get_acc_list using OpenFutureTradeContext, only trading futures accounts will be returned. 

The security_firm is used to filter accounts belonging to the corresponding securities firm, and the filter_trdmarket is used to filter accounts with the corresponding trading market permissions. 

1.1 security_firm 

The brokers currently supported by OpenAPI are as follows. 

When calling get_acc_list, it will return the real account of the securities firm corresponding to security_firm and all paper trading accounts (paper trading has no concept of brokers, so no matter what security_firm is passed, all paper trading accounts will be returned). 

The default value of security_firm is FUTUSECURITIES. You can leave this parameter blank for FUTU HK accounts, but you need to modify this parameter when you want to obtain accounts from other brokers. 

# Example 1

```python
1 trdctx = OpenSecTradeContext安全管理FUTUSECURITIES)  
2 ret, data = trdctx.get_acc_list()  
3 print(data)
```

# Output

```c
1 acc_id trd_env acc_type uni_card_num card_num security_firm sim_acc_type py trdm2 0 281756478396547854 REAL MARGIN 1001200163530138 1001369091153722 FUTUSECERITIES N/A [HK, US, HKCC, HKFUN] 3 1 3450309 SIMULATE CASH N/A N/A N/A STOCK 4 2 3548731 SIMULATE MARGIN N/A N/A N/A OPTION 5 3 281756455998014447 REAL MARGIN N/A 1001100320482767 FUTUSECERITIES N/A 
```

# Example 2

```python
1 trdctx = OpenSecTradeContext安全管理FUTUSG) 2 ret, data = trdctx.get_acc_list() 3 print(data)
```

# Output

```c
1 acc_id trd_env acc_type uni_card_num card_num security_firm sim_acc_type trdmarket_auth acc_status py 2 0 3450309 SIMULATE CASH N/A N/A N/A STOCK [HK] ACTIVE 3 1 3548731 SIMULATE MARGIN N/A N/A N/A OPTION [HK] ACTIVE 
```

# 1.2 filter_trdmarket

The trading markets supported by OpenAPI are as follows. 

When calling get_acc_list, it will return all accounts with trading permissions in the filter_trdmarket market; when the filter_trdmarket is passed as NONE, the market will not be filtered and all accounts will be returned. 

The default trdmarket is HK. Under the universal account system, this parameter is used to filter paper trading accounts in different markets. 

# Example 1

```python
1 trdctx = OpenSecTradeContext.filter_trdmarket=TrdMarket.US) 2 ret, data = trdctx.get_acc_list() 3 print(data) 
```

# Output

```c
1 acc_id trd_env acc_type uni_card_num card_num security_firm sim_acc_type py trdm2 0 281756478396547854 REAL MARGIN 1001200163530138 1001369091153722 FUTUSECERITIES N/A [HK, US, HKCC, HKFUN] 3 1 3450310 SIMULATE MARGIN N/A N/A STOCK 4 2 3548732 SIMULATE MARGIN N/A N/A N/A OPTION 5 3 281756460292981743 REAL MARGIN N/A 1001100520714263 FUTUSECERITIES N/A 
```

# Example 2

1 trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.NONE) 

2 ret, data = trd_ctx.get_acc_list() 

3 print(data) 

py 

# Output

<table><tr><td>1</td><td></td><td>acc_id</td><td>trd_env</td><td>acc_type</td><td>uni_card_num</td><td>card_num</td><td>security_firm</td><td>sim_acc_type</td><td>py trd</td></tr><tr><td>2</td><td>0</td><td>281756478396547854</td><td>REAL</td><td>MARGIN</td><td>1001200163530138</td><td>1001369091153722</td><td>FUTUSECURITIES</td><td>N/A</td><td>[HK, US, HKCC, HKFU]</td></tr><tr><td>3</td><td>1</td><td>3450309</td><td>SIMULATE</td><td>CASH</td><td>N/A</td><td>N/A</td><td>N/A</td><td>STOCK</td><td></td></tr><tr><td>4</td><td>2</td><td>3450310</td><td>SIMULATE</td><td>MARGIN</td><td>N/A</td><td>N/A</td><td>N/A</td><td>STOCK</td><td></td></tr><tr><td>5</td><td>3</td><td>3450311</td><td>SIMULATE</td><td>CASH</td><td>N/A</td><td>N/A</td><td>N/A</td><td>STOCK</td><td></td></tr><tr><td>6</td><td>4</td><td>3548732</td><td>SIMULATE</td><td>MARGIN</td><td>N/A</td><td>N/A</td><td>N/A</td><td>OPTION</td><td></td></tr><tr><td>7</td><td>5</td><td>3548731</td><td>SIMULATE</td><td>MARGIN</td><td>N/A</td><td>N/A</td><td>N/A</td><td>OPTION</td><td></td></tr><tr><td>8</td><td>6</td><td>281756455998014447</td><td>REAL</td><td>MARGIN</td><td>N/A</td><td>1001100320482767</td><td>FUTUSECURITIES</td><td>N/A</td><td></td></tr><tr><td>9</td><td>7</td><td>281756460292981743</td><td>REAL</td><td>MARGIN</td><td>N/A</td><td>1001100520714263</td><td>FUTUSECURITIES</td><td>N/A</td><td></td></tr><tr><td>10</td><td>8</td><td>281756468882916335</td><td>REAL</td><td>MARGIN</td><td>N/A</td><td>1001100610464507</td><td>FUTUSECURITIES</td><td>N/A</td><td></td></tr><tr><td>11</td><td>9</td><td>281756507537621999</td><td>REAL</td><td>CASH</td><td>N/A</td><td>1001100910390035</td><td>FUTUSECURITIES</td><td>N/A</td><td></td></tr><tr><td>12</td><td>10</td><td>281756550487294959</td><td>REAL</td><td>CASH</td><td>N/A</td><td>1001101010406844</td><td>FUTUSECURITIES</td><td>N/A</td><td></td></tr></table>

# Tips

When the filter_trdmarket is passed NONE, all trading accounts will be returned. Row 0 is the active real universal account, rows 1-5 are paper trading accounts, and rows 6-10 are disabled real accounts which are all single-market accounts, that have been replaced by the universal account (row 0). However, historical orders and deals are still in these disabled accounts, and you can query them via these accounts. 

There is no filter_trdmarket in the OpenFutureTradeContext, but security_firm, which has the same function as that in OpenSecTradeContext. 

# 2. Trade API Parameters

When using specific trading API (such as place orders, get open orders), the trd_env , acc_index and acc_id parameters will first filter and confirm a unique account, and then implement the corresponding interface function for this account. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/ddc1b9cae6115ab65c888bcacf49c7c970305fb317ee1cb255f1d55dd6bb1133.jpg)


# Summary

1. Filter out real or paper trading accounts according to trd_env. 

2. Among the results, the account specified by acc_id is prioritized. 

3. If acc_id is 0, select the corresponding account through acc_index. 

4. Error: The specified acc_id does not exist, or the acc_index is out of range. 

# 3. Examples


3.1 Place Orders through Universal securities accounts


1 trdctx = OpenSecTradeContext过滤器_trdmarket=TrdMarket.NONE, security_firm $\equiv$ SecurityFirm.FUTUSECURITIES)   
2 ret，data $=$ trdctx.unlock_trade("123123")   
3 ifret $= =$ RET_OK:   
4 print("unlock success!")   
5 ret，data $=$ trdctx.place_order(45，200，'HK.00700'，TrdSide.BUY, order_type $\equiv$ OrderType.NORMAL,   
6 trd_env $\equiv$ TrdEnv.REAL,   
8 acc_id=0)   
9 print(data)


3.2 Get Open Orders through Universal futures accounts


```python
1 trdctx = OpenFutureTradeContext安全管理FUTUSESECURITIES py  
2  
3 ret, data = trdctx.order_list_query(trd_env=TrdEnv.REAL,  
4 acc_id=0)  
5 print(data)
```


3.3 Get Account Funds through HK Cash Account (Paper Trading)


```python
1 # filter_trdmarket: TrdMarket.HK
2 # trd_env: TrdEnv.SIMULATE
3 # acc_index: 0
4 trdCtx = OpenSecTradeContext过滤器_trdmarket=TrdMarket.HK)
5 ret, data = trdCtx.acinfo_query(trd_env=TrdEnv.SIMULATE, acc_index=0)
6 print(data)
```


3.4 Trade Options through US Margin Account (Paper Trading)


1 #Only two accounts returned after filtering by filter_trdmarket and trd_env py   
2 #acc_index $= 0$ :US Cash Account (Trading stocks)   
3 #acc_index $= 1$ US Margin Account (Trading options)   
4 #acc_index:1   
5 trdctx $\equiv$ OpenSecTradeContext过滤器_trdmarket=TrdMarket.US)   
6 ret，data $\equiv$ trdctx.place_order(10,1，code $\equiv$ "US.AAPL250618P550000"，trdSide $\equiv$ TrdSide.BUY,   
7 trd_env $\equiv$ TrdEnv.SIMULATE,   
8 acc_index $\equiv 1$ 9 print(data)


3.5 Query the Max Quantity that can be Bought or Sold through JP Futures Paper Trading


```python
Print the outcome of get_acc_list, the acc_id of JP Futures Paper Trading is 6271199  
# Pass this acc_id when querying the max quantity that can be bought/sold  
trdctx = OpenFutureTradeContext()  
ret, data = trdctx.acctradinginfo_query(order_type=OrderType.NORMAL, price=5000, trd_env=TrdEnv.SIMULATE, acc_id=6271199, code="JP.NK225main")  
print(data) 
```

# 4. How to map the accounts in OpenAPI to those in the APP?

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/e3a9a137f16b6cf48963fcd15129afe4405c4f3e97672481d46a3150fa46fdac.jpg)


The accounts on the APP only show the last 4-digits of the card number. 

According to the result of get_acc_list, the columns uni_card_num and card_num, are corresponding to the card number of Universal account and Single-market account (disabled), respectively. 

The account obtained in the API can be matched with that on the APP through the last 4 digits of the card number. 

# Others

# Q1： How to build C++ API?

A: futu-api $\mathsf { C } + \mathsf { \Omega } + \mathsf { \Omega } \mathsf { S } \mathsf { D } \mathsf { K }$ is supported on Windows/MacOS/Linux. Pre-built libs are provided for the common build environment on each platform: 

<table><tr><td>OS</td><td>Building Environment</td></tr><tr><td>Windows</td><td>Visual Studio 2013</td></tr><tr><td>Centos 7</td><td>g++ 4.8.5</td></tr><tr><td>Ubuntu 16.04</td><td>g++ 5.4.0</td></tr><tr><td>MacOS</td><td>XCode 11</td></tr></table>

If different compiler version is used, or different protobuf version is used, FTAPI and protobuf may be re-built. FTAPI source directory layout is: 

FTAPI directory structure： 

+---Bin 

+---Include 

+---Sample 

\---Src 

--FTAPI 

+---protobuf-all-3.5.1.tar.gz 

Libs for common build environment 

Public headers, source files generated fro 

Sample project 

FTAPI source 

protobuf source 

# Build steps：

1. Build protobuf to generate libprotobuf static lib and protoc executable. 

2. Generated ${ \mathsf { C } } + +$ source files from proto files. 

3. Build FTAPI to generate libFTAPI static lib 

# Step1: Build protobuf：

. Windows： 

Install CMake 

Open Visual Studio command prompt, change directory to protobuf/cmake 

Run：cmake -G "Visual Studio 12 2013" -DCMAKE_INSTALL_PREFIX $=$ install - Dprotobuf_BUILD_TESTS=OFF  This will generate Visual Studio 2013 solution file. Change -G parameter for other Visual Studio versions. 

Open Visual Studio solution file, set platform toolset to v120_xp, then build. 

. Linux (Refer to protobuf/src/README) 

Run ./autogen.sh 

Run CXXFLAGS $=$ "-std $=$ gnu++11" ./configure --disable-shared 

Run make 

Put generated libprotobuf.a in Bin/Linux 

. MacOS (Refer to protobuf/src/README) 

Install dependencies with brew：autoconf automake libtool 

Run ./configure CC=clang CXX="clang $^ { + + }$ -std=gnu++11 -stdlib $=$ libc++" --disableshared 

# Step2: Generate ${ { \mathsf { C } } + + }$ sources from proto files

Use protoc to convert protofiles under Include/Proto to ${ \mathsf { C } } + +$ source files. For example, the following command converts Common.proto to Common.pb.h and Common.pb.cc: 

protoc -I="path-to-FTAPI/Include/Proto" --cpp_out $= "$ "." path-to-FTAPI/Include/Proto/Common.proto 

. Put the generated .h and .cc files in Include/Proto 

# Step3: Build FTAPI

Windows：Create Visual Studio ${ \mathsf { C } } + +$ static lib project，add source files under Src/FTAPI and Include，and set platform toolset to v120_xp. 

Mac：Create XCode ${ \mathsf { C } } + +$ static lib project，add source files under Src/FTAPI and Include 

Linux：Use cmake to build FTAPI static lib, run following command under path-to-FTAPI/Src: cmake -DTARGET_OS=Linux 

# Q2: Is there more complete strategy examples for reference?

A: 

Python strategy examples are in the /futu/examples/ folder. You can find the path of Python API by executing the following command: 

```txt
1 import futu   
2 print(futu._file_) 
```

The C# strategy examples are in the /FTAPI4NET/Sample/ folder 

The Java strategy examples are in the /FTAPI4J/sample/ folder 

The ${ \mathsf { C } } + +$ strategy examples are under the /FTAPI4CPP/Sample/ folder 

The JavaScript strategy examples are in the /FTAPI4JS/sample/ folder 

# Q3: Import error when using python API

A: 

# First Scene:

I have already installed futu-api, but still get error: No module named 'futu'? 

It is possible that the interpreter your IDE currently uses is not the interpreter of the futu-api module you installed. In other words, your may have more than two Python environments installed on your computer. You can do the following 2 steps: 

1. Run the codes below to get the path of the current interpreter: 

```python
1 import sys   
2 print(sys.executable) 
```

Example diagram: 

```txt
In[3]: import sys
...
print(sys.executable)
D:\software\anaconda3\python.exe 
```

2. Run $^ { - 1 }$ D:\software\anaconda3\python.exe -m pip install futu-api in command line (The first half of the command comes from the result of step 1). This will install a futuapi module in the current interpreter. 

# Q4: Import successful, but you still cannot call the relevant interface.

A: Usually in this case, you need to check if the ‘futu’ that was successfully imported is a correct Futu API. 

First Scene: There may be a file with the same name as 'futu'. 

1. The current file name is futu.py 

2. There is another file named futu.py under the path of the current file. 

3. There is a folder named /futu under the path of the current file. 

Therefore, we strongly recommend that you do not name files / folders / projects as futu. 

Second Scene: A third-party library called 'futu' was installed by mistake. 

The correct name of the Futu API library is futu-api , not 'futu'. 

If you have installed a third-party library named 'futu', please uninstall it and install futu-api. 

Take PyCharm as an example: Check the installation of libraries. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/e25ea4659dfd816d546c0af925f4601dafb9d42e1a4a580b5cc369fa729aef11.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/c41bc296ebf7b296e2bbfa0adbd5e031fe2019e2e4e87c7187bb13304fc38eca.jpg)


# Q5: Protocol Encryption-Related

A: 

Overview 

To ensure privacy and confidentiality, you can use the asymmetric encryption algorithm RSA to encrypt the request and return between Strategy Scripts (Futu API) and OpenD. 

If Strategy Scripts (Futu API) is on the same computer as OpenD, it is usually not necessary to encrypt. 

# Protocol Encryption Process

You can try to solve this problem with the following steps: 

1. Generate the key file automatically through a third-party web platform. 

To be specific: Search 'Online RSA Key Generator' on Baidu or Google. Set Key Format as PKCS#1. Set Key Length as 1024 bit. No password required. Then click the bottom 'Generate key pair' 

Generate key pair 

mIB5eJs9zroWtetUk4rdY4D5NAH0BXoT50KSwY1107+YSnkfzNTmn1jLaoYGf5VF At+MoHogSzfrLG7WU1f7wIiVBGb/F1Ouirol0Fm969Au6Zi0S2UcZ9di5ERaMszF QvQrb9KFnev1I32LLx2s4brDrc011mWhKeSQmfY3YsgQtFyG/52zd9J5GUMWPHRH Tk99bi3gJre9jovU85LBgZC3KMN80RraYpzjpD0WQ/GQ1WFkkbG0On0H5Y68dA8k 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/7e7f3ade6232d47df2bedc3bdd0f94bbf0a4fe6bcc3b11b988c30881158402d1.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/2803b1c5b36db6c2bc77d80e95475fe40872a33d006708149d1a0efa59a0293d.jpg)


2. Copy and paste the private key into a text file. Save it to a specified path of the computer which OpenD is located in. 

3. Specify the path of the RSA private key file on the computer which OpenD is located in. The path is the specified path mentioned in Step 2. 

Method 1: Specify the path mentioned in Step 2 through 'Encryption Private Key' in Visualization OpenD. As shown below: 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/c2aa55b0dbbf5fafe062165bca3cd60d32ca42010a3b9e921e0bfff62ad53841.jpg)


# Futu OpenD Login

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/d45754394c279581aa949212240fd89be5913f826e1cfc95760aaadd05b9b69e.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/7a30b511c5ed4267f8bd4d159a8b74e81cc44946acf56e2cb772ce3cd9446cc4.jpg)


# Basic

Advanced 

Telnet will not work if not set 

Method 2: Specify the path mentioned in Step 2 through the code rsa_private_key in Command Line OpenD. As shown below: 

```txt
futu_open>   
<-- 基础参数 -->   
<!-- Basic parameters -->   
<!-- 协议监听地址，不填默认127.0.0.1 -->   
<!-- Listening address. 127.0.0.1 by default -->   
<ip>127.0.0.1</ip>   
<!-- API接口协议监听端口 -->   
<!-- API interface protocol listening port -->   
<api_port>11112</api_port>   
<!-- 登录帐号 -->   
<!-- Login account -->   
<login_account>100001</login_account>   
<!-- 登录密码32位MD5加密16进制 -->   
<!-- Login password, 32-bit MD5 encrypted hexadecimal -->   
<!-- <login pwd md5>6e55f158a827b1a1c432la245aaaad88</login pwd md5> -->   
<!-- 登录密码明文，密码密文存在情况下只使用密文 -->   
<!-- Plain text of login password. When cypher text exists, the cypher text will be used. -->   
<login pwd>123456</login pwd>   
<!-- FutuOpenD语言，en：英文，chs：简体中文 -->   
<!-- FutuOpenD language. en: English,chs: Simplified Chinese -->   
<lang>chs</lang>   
<-- 进阶参数 -->   
<!-- Advanced parameters -->   
<!-- FutuOpenD日志等级，no, debug, info, warning, error, fatal -->   
<!-- FutuOpenD log level: no, debug, info, warning, error, fatal -->   
<log_level>info</log_level>   
<!-- API推送协议格式，0: pb, 1: json -->   
<!-- API push protocol format. 0: pb, 1: json -->   
<pushProto_type>0</pushProto_type>   
<!-- API订阅数据推送频率控制，单位毫秒，目前不包括K线和分时，不设置则不限制频率-->   
<!-- Data Push Frequency, in milliseconds. Candlesticks and timeframes are not included. If not set, the frequency will be 0.0.0.1-->   
<!-- <got push frequency>1000</got push frequency> -->   
<!-- Telnet监听地址，不填默认127.0.0.1 -->   
<!-- Telnet listening address. 127.0.0.1 by default -->   
<!-- <telnet_ip>127.0.0.1</telnet_ip> -->   
<!-- Telnet监听端口 -->   
<!-- Telnet listening port -->   
<!-- <telnet_port>22222</telnet_port> -->   
<!-- API协议加密私钥文件路径，不设置则不加密 -->   
<!-- File path for private key for API protocol encryption. If not set, it will not be encrypted. -->   
<!-- <rsa private key>D:\rsa</rsa private key> -->   
<-- 是否接收到价提醒推送，0：不接收，1：接收 -->   
<-- Whether to receive the price reminder push. 0: not receive, 1: receive -->
```

4. Save the text file in step 2 to a specified path of the computer which Strategy Scripts (Futu API) are located in, and set the path of private key in Strategy Scripts. 

5. Enable protocol encryption. There are two ways to enable protocol encryption. 

Method 1: Encrypt the context independently (general). You can set encryption through the parameter is_encrypt when creating and initializing the connection in Quote Object or Transaction Objects. 

Method 2: Encrypt the context globally (only Python). You can set encryption through the interface enable_proto_encrypt. 

# Tips

When specifying the path of RSA private key in OpenD or in Strategy Scripts (Futu API), the path needs to be complete and include the file name. 

It is not necessary to save RSA public key which can be calculated by private key. 

# Q6: Why is the DataFrame data I got incomplete?

A: When printing pandas.DataFrame data, if there are too many columns and rows, pandas will collapse the data by default, resulting in an incomplete display. 

Therefore, it is not OpenD's fault. You can add the following code in front of your Python script to solve the problem. 

import pandas as pd 

pd.options.display.max_rows=5000 

pd.options.display.max_columns=5000 

pd.options.display.width=1000 

# Q7: How to solve the problem that "Cannot open libFTAPIChannel.dylib" through C++ API on Mac?

A: Execute the following command in the directory where the file "libFTAPIChannel.dylib" is stored: $\because$ xattr -r -d com.apple.quarantine libFTAPIChannel.dylib 

Q8: For Python users, why do large log files continue to be generated under the log folder, after the log level is 

A：The log_level parameter in OpenD parameter configuration is only used to control the logs generated by OpenD. Python API also generates logs by default. 

If you do not like it, you can add the following codes to your Python script: 

1 2 

logger.file_level = logging.FATAL # Used to stop Python API log files generating logger.console_level = logging.FATAL # Used to stop printing Python log in runn 

# Q9: For versions 5.4 and above, the library name and configuration method of Java API have been changed.

A: 

If you are a user of Java API 5.3 and below, please note the following changes when updating the version. 

Changes to the configuration process: 

1. Download Futu API from Futubull official website . 

2. Decompress the downloaded file. /FTAPI4J is the directory of Java API. Add /lib/futu-api-.x.y.z.jar file to your project settings. To establish a futu-api project, please refer to here. 

# Changes to the directory:

1. For the Java version of Futu API, the library name is changed from ftapi4j.jar to futuapi-x.y.z.jar , where "x.y.z" represents the version number. 

2. For the third-party library, the dependencies of /lib/jna.jar and /lib/jna-platform.jar are removed, and the dependencies of /lib/bcprov-jdk15on-1.68.jar and /lib/bcpkix-jdk15on-1.68.jar are added. 

1
2
3
4
5
6 

+---ftapi4j 

--lib 

futu-api-x.y.z.jar 

| bcprov-jdk15on-1.68.jar 

bcpkix-jdk15on-1.68.jar 

| protobuf-java-3.5.1.jar 

FTAPI4J source code. If the JDK version used 

The folder with common libraries 

Java version of Futu API 

Third-party library, for encryption and decry 

Third-party library, for encryption and decry 

Third-party library, for parsing protobuf dat 

7 

+---sample 

8 

--resources 

Sample project 

The default generated directory of the maven 

If you are a new user to the Futu API, we provide a more convenient way to configure Java API via maven repository for you. About the configuration process, please refer to here. 

# Q10: For Python users, when using pyinstaller to package scripts that need to run api, an error is reported: Common_pb2 module cannot be found.

A: You can try to solve this problem with the following steps. 

Step 1. Suppose you need to package main.py. Using a command-line statement and run the statement: pyinstaller path\main.py, without the "- F" parameter. 

1 

pyinstaller path\main.py 

After main.py is packaged, the /main folder will be created in the /dist directory where it is located. main.exe is in this folder. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/173e7e20ea50cc3cfb36beae6a4a58818285094abf49280ba5acec9785669c26.jpg)


.idea 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/7204a7877b4ed25f3f282d473e906f6c618034e9eb8c6ee0f545252bbb0f80b7.jpg)


_pycache 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/9c2dcebc288eb321d67a2ff0366b7d2d40b8a0af6666f8f404f0df96ec9f7b8c.jpg)


build 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/1fc392803eedb4af8b6fa77ebfda6eed4ce449fe6be1bea5f43f29a789ba852f.jpg)


dist 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/e0db7f187fcec6085c197f2f29c0c00abc5d96d6438f26348fbe9446fb915b4b.jpg)


futu 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/5bade4e4eb6c9066b88cf70cd7cc4b01178bb111cef6b92f6c3a086880403536.jpg)


main.py 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/ef670fc6448cdfcb22cb460ecff22a73caf56023e98b7c05713f54b3ef6e4280.jpg)


main.spec 

Step 2. Run the following code to find the installation path of futu-api: /path/futu. 

1 

import futu 

2 

print(futu.__file__) 

Results: 

1 

C:\Users\ceciliali\Anaconda3\lib\site-packages\futu\__init__.py 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/62cc11357b2acc3826f845e13995e02dc0e1e7ab96d05148649ab40d5d5ced77.jpg)


Step 3. Copy all the files in the /common/pb to /main. 

Step 4. Create a folder in the /main and name it futu. Copy the /path/futu/VERSION.txt file to /main/futu. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/ab47429199d8d1e2478fea04a858d91e0c6caa8e2b283d333abf5e346d0c072c.jpg)


Step 5. Try running the statement pyinstaller main.py again. 

Q11: Why the interface result is success, but the return did not behave as expected？ 

A: 

A successful interface result means that server has successfully received and responded to your request, but the return may not behave as your expected. 

Example: If you call the subscribe during non-trading hours, your request can be responded successfully, but the exchange will not update the ticker data during this period. So you will temporarily not receive real-time data until trading hours. 

The interface result (definition: Interface Result) can be viewed from the field returned. A field of 0 means the interface result success, a non-zero means the interface result failed. 

For python user, the following two code statements are equivalent: 

```txt
1 if ret_code == RET_OK: 
```

1 if ret_code $= = 0$ 

# Q12: WebSocket Related

# Overview

In OpenAPI, WebSocket is mainly used in the following two aspects: 

In Visualization OpenD, WebSocket is used to communicate between the UI interface and the underlying Command Line OpenD. 

The communication between JavaScript API and OpenD uses WebSocket. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/b523886bb28f74f9790d185bfb8bd054384052beb2e77470d4068b9f1c88cccf.jpg)


When WebSocket starts, Command Line OpenD establishes a Socket connection (TCP) with the FTWebSocket transit service. This connection uses the default listening address and API protocol listening port. 

At the same time, JavaScript API will establish a WebSocket connection (HTTP) with the FTWebSocket transit service. This connection will use the WebSocket listening address and WebSocket port. 

# Usage

To ensure the security of your account, when WebSocket listens non-local requests, we strongly recommend that you enable SSL and configure the WebSocket authentication key 

SSL is enabled by configuring the WebSocket certificate and the WebSocket private key. Command Line OpenD can set the file path by configuring OpenD.xml or configuring command line parameters. Visualization OpenD clicks the "more" drop-down menu to see the confifuration item. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/ca482f0808bb2291250f1846287ee916aa450b3c3dcf09147b3a45672cd0b8c2.jpg)


# Futu OpenD Login

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/cc99b26d29b81649036c79c2a975b1cc58dc1d5b7f7874b56b06d66552b9ec04.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/da3d262376cd44bfc9b825640535f400f5ab311c2bf664ab6ca924faa903e137.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/213a8fb8c9b9a62f1fc4e29e97016b5a784a5cc6ad7bd1d56bfc37fe853150e2.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/9953a41273b2741a12571ee0dcee5ba740c1228269de947483c5c8e8fa535ae7.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-19/fad76b6f-dc3f-447c-b13a-43c79c284ba1/25b72bfcc92f4dbf26b7e851645a431551fb4dd18e270a0e2aa40b1122ec1057.jpg)


# Tips

If the certificate is self-signed, you need to install the certificate on the machine where the JavaScript API is called, or set not to verify the certificate. 

# Generate Self-signed Certificate

It is not convenient to expand the details of self-signed certificate generation in this document, please check it yourself. Simple and available build steps are provided here: 

1. Install openssl. 

2. Modify openssl.cnf and add the IP address or domain name under the alt_names node on the machine where OpenD locates. 

For example: IP.2 = xxx.xxx.xxx.xxx, DNS.2 = www.xxx.com 

3. Generate private key and certificate (PEM)。 

The certificate generation parameters are as follows： 

openssl req -x509 -newkey rsa:2048 -out futu.cer -outform PEM -keyout 

# Tips

openssl.cnf needs to be placed under the system path, or an absolute path needs to be specified in the build parameters. 

Note that while generating a private key, you need to specify that the password is not set (-notes). 

Attach the local self-signed certificate and the configuration file that generates the certificate for testing: 

. openssl.cnf 

. futu.cer 

futu.key 

# Q13: Where are the quote servers and the trade servers of OpenAPI?

A： 

Quote: 

<table><tr><td>Futu ID</td><td>Quote Server Location</td></tr><tr><td>Futubull ID</td><td>Tencent Cloud Guangzhou and Hong Kong</td></tr><tr><td>moomoo ID</td><td>Tencent Cloud Virginia, USA and Singapore</td></tr></table>

. Trade: 

<table><tr><td>Securities Firm</td><td>Trade Server Location</td></tr><tr><td>FUTU HK</td><td>Tencent Cloud Hong Kong</td></tr><tr><td>Moomoo US</td><td>Tencent Cloud Virginia, USA</td></tr><tr><td>Moomoo SG</td><td>Tencent Cloud Singapore</td></tr><tr><td>Moomoo AU</td><td>Tencent Cloud Singapore</td></tr><tr><td>Moomoo MY</td><td>Ali Cloud Malaysia</td></tr><tr><td>Moomoo CA</td><td>AWS Cloud Canada</td></tr><tr><td>Moomoo JP</td><td>Tencent Cloud Japan</td></tr></table>

# Q14: The Guide for Universal Account Upgrade

# 1. Universal Account Upgrade

The universal account allows trading securities, futures, and forex across various markets using multiple currencies within one account. Upgrading one or multiple single-market accounts to a universal account involves migrating under your old account. This includes: 

. Creating a universal account 

Transferring assets from your existing single-market account to the universal account 

Closing the single-market account 

# 2. OpenD Version Upgrade

We are scheduled to upgrade your accounts to universal accounts on September 14th and 15th, 2024. Please check your OpenD and API versions in advance. 

# . Version 7.01 and below

Due to the outdated versions, OpenD will discontinue service on September 14th, 2024, during which you will be logged out of OpenD automatically. We recommend upgrading your OpenD and API to the latest version before September 14th, and stopping any live trading strategies over the weekend of September 14th to 15th. 

# . Version 7.02 to 8.2

Due to the older versions, OpenD no longer supports universal accounts. We recommend upgrading your OpenD and API to the latest version before September 14th, and stopping any live trading strategies over the weekend of September 14th to 15th. 

# . Version 8.3 and above

You can use these versions normally. However, we also recommend not running any live trading strategies over the weekend of September 14th to 15th. 

After upgrading, your assets will be transferred to the new universal account, causing strategies targeting the old account to malfunction. We recommend conducting necessary checks and tests before live trading, to ensure everything is set up properly. 

# 3. Changes in OpenAPI after the OpenD upgrade

Python API will no longer support creating transaction objects with OpenHKTradeContext, OpenUSTradeContext, OpenHKCCTradeContext, and OpenCNTradeContext. Please refer to the Create the connection, and use OpenSecTradeContext instead. 

For non-Python API users, when using the Trd_GetAccList, please set the needGeneralSecAccount to true in order to get Universal account information. 

. Add Account Status 

When using the Get the List of Trading Accounts, the results will now include an acc_status field. 

The universal accounts are marked as ACTIVE 

The old single-market accounts are marked as DISABLED 

Changes in Trading API: Place Orders, Modify or Cancel Orders, Query the Maximum Quantity that Can be Bought or Sold 

Executing transactions and querying purchasing power can only be allowed via the acc_id or acc_index of ACTIVE accounts. 

Using the acc_id or acc_index of DISABLED accounts will cause errors. 

Python API：please specify the acc_id as the upgraded universal account. 

Non-Python API：in the TrdHeader, please specify the accID as the upgraded universal account. 

# 4. Need help?

# Team Support

If you encounter any issues during the upgrade process or while using the universal account, you can contact our technical/product teams through official channels. 

# Stay Focused

We will continue to publish the latest notifications and assistance information through Futu API Doc, emails, APP messages, QQ, etc. Please pay attention to official updates. 