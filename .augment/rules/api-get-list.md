---
type: "always_apply"
---

2.接口交互方式
	东华医为科技有限公司与第三方PACS系统采用WebService+XML的接口方式进行数据交互。

交互接口说明：
功能说明	根据交互操作服务编码和具体的消息流进行相应的交互操作
通讯方式	WebService+Xml
服务地址	https://192.168.206.193:1443/csp/hsb/DHC.Published.PISWebService.BS.PISWebService.CLS?WSDL=1
方法名	HIPMessageServer(入参1 input1,入参2 input2)
	1、action类型为字符串，服务编号传给该参数
    2、message类型为标准消息请求流传给该参数

申明：所有服务中“示例”仅用于说明Xml的总体结构，具体到每个字段的属性名以“请求消息”、“应答消息”定义中为准。


5.1申请信息列表 —第三方拉取
接收检查申请单信息
接口方式	XML+WebService
服务编码	MES0201
服务名称	拉取检查申请单信息列表
服务提供者	平台
服务调用者	第三方检查系统
调用时机	第三方主动拉取患相关检查信息列表
HIS推送第三方系统

请求消息：

代码	名称	数据类型	是否必输	备注
SourceSystem	消息来源	VARCHAR(50)	NOT NULL	
MessageID	消息ID	VARCHAR(30)	NOT NULL	
Body	入参集合			
CardValue	患者索引	VARCHAR(30)	NOT NULL	
CardTypes	患者索引类型	VARCHAR(30)	NOT NULL	1：医嘱号；
2：登记号；
3：就诊卡号；
4：住院号（病案号）
5：证件号
ExeLoc	检查执行科室代码	VARCHAR(50)	NOT NULL	
EpsiodeType	就诊类型	VARCHAR(50)		为空：全部；
I：住院；
E：急诊；
O：门诊、体检

示例
<Request>
    <Header>
        <SourceSystem>RuiKe</SourceSystem>
        <MessageID>98753-37181-37208</MessageID>
    </Header>
    <Body>
        <CardValue>0000000014</CardValue>
        <CardTypes>2</CardTypes>
        <ExeLoc>静秀路放射科</ExeLoc>
        <EpsiodeType>I</EpsiodeType>
    </Body>
</Request>

应答消息：
代码	名称	数据类型	是否必输	备注
SourceSystem	消息来源		NOT NULL	
MessageID	消息ID		NOT NULL	
ResultCode	响应码		NOT NULL	0：成功 -1:失败
ResultContent	响应信息		NOT NULL	
PatOrdLists	检查单列表
PatOrdList	检查单信息列表
HospitalCode	医院代码			
HospitalDesc	医院名称			
PATPatientID	登记号		NOT NULL	患者主索引
PAADMVisitNumber	就诊流水号		NOT NULL	就诊信息主索引
RISRAppNum	申请单号		NOT NULL	
PAADMTypeCode	就诊类型代码			O：门诊、体检
E：急诊
I：住院
P：预住院
PAADMTypeDesc	就诊类型描述			
PATName	患者姓名			
PAADMCurBedNo	床号			
PATSexCode	性别代码			
PATSexDesc	性别描述			
PATAge	年龄			
PATDob	出生日期			
PATIdentityNum	身份证号			
OEORIOrderItemID	医嘱ID		NOTT NULL	医嘱主索引，获取申请单明细的入参
RISRCode	医嘱代码			
RISRDesc	医嘱描述			
RISRExternalCode	医嘱外部代码			
RISRExternalDesc	医嘱外部代码			
OrdBillStatus	收费状态			
RISRPrice	医嘱价格			
AppDeptCode	开单科室代码			
AppDeptDesc	开单科室描述			
RISRSubmitDocCode	开单医生工号			
RISRSubmitDocDesc	开单医生姓名			
RISRSubmitDate	开单日期			
RISRSubmitTime	开单时间			
RISRAcceptDeptCode	检查科室代码			
RISRAcceptDeptDesc	检查科室描述			
OrdSubCatCode	医嘱子分类代码			
OrdSubCatDesc	医嘱子分类描述			
示例
<Response>
    <Header>
        <SourceSystem>02</SourceSystem>
        <MessageID>19</MessageID>
    </Header>
    <Body>
        <ResultCode>0</ResultCode>
        <ResultContent>查询成功</ResultContent>
        <PatOrdLists>
            <PatOrdList>
                <HospitalCode>H51010402507</HospitalCode>
                <HospitalDesc>四川锦欣西囡妇女儿童医院</HospitalDesc>
                <PATPatientID>0000000014</PATPatientID>
                <PAADMVisitNumber>40</PAADMVisitNumber>
                <RISRAppNum>APPI2025011400003</RISRAppNum>
                <PAADMTypeCode>I</PAADMTypeCode>
                <PAADMTypeDesc>住院</PAADMTypeDesc>
                <PATName>产科测试</PATName>
                <PAADMCurBedNo>702</PAADMCurBedNo>
                <PATSexCode>2</PATSexCode>
                <PATSexDesc>女</PATSexDesc>
                <PATAge>37岁</PATAge>
                <PATDob>1987-12-12</PATDob>
                <PATIdentityNum>500225198712123029</PATIdentityNum>
                <OEORIOrderItemID>39||16</OEORIOrderItemID>
                <RISRDesc>单次多层CT增强扫描  (胸部)</RISRDesc>
                <RISRCode>20101107003</RISRCode>
                <RISRExternalDesc></RISRExternalDesc>
                <RISRExternalCode></RISRExternalCode>
                <OrdBillStatus>未收费</OrdBillStatus>
                <RISRPrice>550</RISRPrice>
                <AppDeptCode>静秀路产科一区</AppDeptCode>
                <AppDeptDesc>7楼产科一区</AppDeptDesc>
                <RISRSubmitDocCode>ys01</RISRSubmitDocCode>
                <RISRSubmitDocDesc>医生01</RISRSubmitDocDesc>
                <RISRSubmitDate>2025-01-14</RISRSubmitDate>
                <RISRSubmitTime>13:08:24</RISRSubmitTime>
                <RISRAcceptDeptCode>静秀路放射科</RISRAcceptDeptCode>
                <RISRAcceptDeptDesc>放射科(静秀路)</RISRAcceptDeptDesc>
                <OrdSubCatCode>1502</OrdSubCatCode>
                <OrdSubCatDesc>检查CT</OrdSubCatDesc>
            </PatOrdList>
            <PatOrdList>
                <HospitalCode>H51010402507</HospitalCode>
                <HospitalDesc>四川锦欣西囡妇女儿童医院</HospitalDesc>
                <PATPatientID>0000000014</PATPatientID>
                <PAADMVisitNumber>40</PAADMVisitNumber>
                <RISRAppNum>APPI2025011400003</RISRAppNum>
                <PAADMTypeCode>I</PAADMTypeCode>
                <PAADMTypeDesc>住院</PAADMTypeDesc>
                <PATName>产科测试</PATName>
                <PAADMCurBedNo>702</PAADMCurBedNo>
                <PATSexCode>2</PATSexCode>
                <PATSexDesc>女</PATSexDesc>
                <PATAge>37岁</PATAge>
                <PATDob>1987-12-12</PATDob>
                <PATIdentityNum>500225198712123029</PATIdentityNum>
                <OEORIOrderItemID>39||17</OEORIOrderItemID>
                <RISRDesc>单次多层CT增强扫描  (下腹部)</RISRDesc>
                <RISRCode>20101107005</RISRCode>
                <RISRExternalDesc></RISRExternalDesc>
                <RISRExternalCode></RISRExternalCode>
                <OrdBillStatus>未收费</OrdBillStatus>
                <RISRPrice>550</RISRPrice>
                <AppDeptCode>静秀路产科一区</AppDeptCode>
                <AppDeptDesc>7楼产科一区</AppDeptDesc>
                <RISRSubmitDocCode>ys01</RISRSubmitDocCode>
                <RISRSubmitDocDesc>医生01</RISRSubmitDocDesc>
                <RISRSubmitDate>2025-01-14</RISRSubmitDate>
                <RISRSubmitTime>13:08:24</RISRSubmitTime>
                <RISRAcceptDeptCode>静秀路放射科</RISRAcceptDeptCode>
                <RISRAcceptDeptDesc>放射科(静秀路)</RISRAcceptDeptDesc>
                <OrdSubCatCode>1502</OrdSubCatCode>
                <OrdSubCatDesc>检查CT</OrdSubCatDesc>
            </PatOrdList>
        </PatOrdLists>
    </Body>
</Response>

