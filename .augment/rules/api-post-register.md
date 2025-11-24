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


5.7文档注册
文档注册
接口方式	XML+WebService
服务编码	详见4.业务数据交互服务列表
服务名称	文档注册RegisterDocument
服务提供者	平台
服务调用者	第三方系统
调用时机	第三方报告文档生成后调用

请求消息：
代码	名称	数据类型	是否必输	备注
SourceSystem	消息来源	VARCHAR(50)	NOT NULL	
MessageID	消息ID	VARCHAR(30)	NOT NULL	
OrganizationCode	医疗机构编码	VARCHAR(30)	NOT NULL	默认传0001
PATPatientID	患者主索引	VARCHAR(30)	NOT NULL	患者在医疗机构的唯一标识
PATPatientName	姓名	VARCHAR(30)	NOT NULL	
PAADMVisitNumber	就诊号码	VARCHAR(30)	NOT NULL	患者每次就诊的唯一标识
RISRExamID	检查号	VARCHAR(50)		
SpecimenID	样本号（条码号）	VARCHAR(20)		
OEORIOrderItemID	医嘱明细ID	VARCHAR(20)		
DocumentType	文档类别	VARCHAR(3)	NOT NULL	02001	放射
02002	超声
02003	内镜
02004	心电
02005	核医学
02006	病理报告

DocumentID	文档ID	VARCHAR(30)	NOT NULL	源系统内该文档唯一标识
DocumentContent	文档内容		NOT NULL	具体文档内容见临床文档,内容转换成BASE64格式
按报告类型见附录二、附录三
DocumentPath	文档路径	VARCHAR(100)	NOT NULL	http链接的pdf地址

DocumentPicPath	图像路径	VARCHAR(100)	NOT NULL	
UpdateUserCode	最后更新人编码	VARCHAR(20)	NOT NULL	
UpdateDate	最后更新日期	DATE	NOT NULL	YYYY-MM-DD
UpdateTime	最后更新时间	TIME	NOT NULL	hh:mm:ss

示例
<Request>
    <Header>
        <SourceSystem></SourceSystem>
        <MessageID></MessageID>
    </Header>
    <Body>
        <RegisterDocumentRt>
            <OrganizationCode></OrganizationCode>
            <PATPatientID></PATPatientID>
            <PATPatientName>秦海贤</PATPatientName>
            <PAADMVisitNumber></PAADMVisitNumber>
            <RISRExamID></RISRExamID>
            <SpecimenID></SpecimenID>
            <OEORIOrderItemID></OEORIOrderItemID>        
            <DocumentType></DocumentType>
            <DocumentID></DocumentID>
            <DocumentContent></DocumentContent>
            <DocumentPath></DocumentPath>
            <DocumentPicPath></DocumentPicPath>
            <UpdateUserCode></UpdateUserCode>
            <UpdateDate></UpdateDate>
            <UpdateTime></UpdateTime>
        </RegisterDocumentRt>
    </Body>
</Request>
应答消息：
代码	名称	数据类型	是否必输	备注
SourceSystem	消息来源	VARCHAR(50)	NOT NULL	
MessageID	消息ID	VARCHAR(30)	NOT NULL	
ResultCode	响应码	VARCHAR(6)	NOT NULL	0：成功 -1:失败
ResultContent	响应信息	VARCHAR(300)	NOT NULL	

示例
<Response>
	<Header>
		<SourceSystem></SourceSystem>
		<MessageID></MessageID>
	</Header>
	<Body>
		<ResultCode>0</ResultCode>
		<ResultContent>成功</ResultContent>
	</Body>
</Response>
