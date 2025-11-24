---
type: "always_apply"
---

Xcope API 接⼝文档

Xcope API 是由北京英特美迪科技有限公司开发的⼀款基于 Web API 的接⼝ , 这些接⼝都是标准的 RESTful API,  通过 HTTP 协议进⾏通信, 以 JSON 格式进⾏数据交互, 适⽤于各种语⾔的开发. 由于所有的API都有访问权限, 唯 ⼀调⽤的⽅法需要通过 oAuth2 的 client_credentials ⽅式进⾏授权, 以获取访问权限, 所以在使⽤ API 之前, 需要 先了解 oAuth2 的授权⽅式, 以及如何获取访问权限.

先决条件
在和此产品进⾏交互之前, 需要先和我公司⼈员进⾏联系, 以获取访问权限.
.  Client ID: ⽤于标识客户端的 ID,
.  Client Secret: ⽤于标识客户端的 Secret, .  API 地址: ⽤于访问 API 的地址,
测试
在获取到以上信息之后, 可以通过 Postman 进⾏测试, 以确保能够正常访问 API. 
测试用：
client_id: Xcope_ExternalApi
client_secret: 123456
注意
.  在着⼿软件的调试前, 请确保⽹络通畅, 以及能够正常访问 API. .  最近更新于 2024年10⽉8⽇
.  以下演示API地址ip假定为127.0.0.1，实际使用请根据实际机器的ip进行替换

获取 AccessToken
简要描述

.  本章节介绍如果通过 client credentials 获取 access token. 具体的 client_id 和 client_secret 请与公司⼈员 联系获取

请求URL

.  http://127.0.0.1:9601/connect/token

请求⽅式

   POST
参数

参数名                必选      类型          说明                                                                位置

client_id	是	string	client 标识		x-www-form-urlencodeed
client_secret	是	string	client secret		x-www-form-urlencodeed
scope	是	string	scope 默认传入 Xcope		x-www-form-urlencodeed
grant_type        是     string        授权⽅式 请设置为 client_credentials    x-www-form-urlencodeed

返回⽰例


{
"access_token":
"eyJhbGciOiJSUzI1NiIsImtpZCI6IjI0RThBMkZCOUJDOEExMUVBQjk0RkNGNjYyOEMwODkwIiwidHlwI joiYXQrand0In0.eyJuYmYiOjE2NDA4MzIwNjIsImV4cCI6MTY3MjM2ODA2MiwiaXNzIjoiaHR0cDovLzE 5Mi4xNjguMi4yNDI6OTgwMiIsImF1ZCI6IkFwcCIsImNsaWVudF9pZCI6IkFwcF9BcHAiLCJpYXQiOjE2N DA4MzIwNjIsInNjb3BlIjpbIkFwcCJdfQ.i4fh04EONfd4yF4YdjtLQmPX3Jsed3tSf9LIX7Xn8WehrhvX n6nliA06qDi5u6_0IjCItMBL6--
jGwTQfLiXjmlcC6r322YZzd9UCgkw3h8wy3Ofgl90psHifFegsoaAP0-yYcMjh7soGH1ULYt0- hfVJPbqy6IDgXktk-NEbm4dpetUTQ8d6tszmC8dPqp9iuoN4_lLRy-
3QyvRxDlDEClbsK8HqIoMJXxUZnomh9G5iHzKx41qN1OgoZlhmYQvP_2YgdcZmmNytEwDQYqDlca_rnvu- 1qlGPpmQBlG6v_Bg1jBRP_fDmVADZ-4T5v6KJdytrYBjUUw7Sz6h-0vmQ",
"expires_in": 31536000, "token_type": "Bearer", "scope": "App"
}

返回参数说明

参数名                 类型        说明

access_token	string	授权令牌
expires_in	int	有效期， 以秒为单位
token_type	int	令牌类型
scope                 int          作⽤域
获取报告列表
简要描述

.  获取报告列表, 通过查询条件返回报告列表, ⽀持分⻚和排序

请求URL

·    http://127.0.0.1:9601/api/app/report-entries/entry-fields
请求⽅式

   GET

参数

参数名                                必选      类型               说明

startDate	否	DateTime	查询开始时间,格式为YYYY-MM-DDThh:mm
EndDate	否	DateTime	查询结束时间,格式为YYYY-MM-DDThh:mm
Name	否	string	报告对象姓名
InspectSender	否	string	送检医师
DepartmentCategory	否	string	送检科室
SkipCount	否	int	Skip 个数,⽤于分⻚
MaxResultCount             否          int                  获取最⼤数量,⽤于分⻚

返回⽰例




"上⽪细胞": "-",  "⽩细胞": "0-5",  "乳杆菌": "++++", "杂菌": "+",
"基底上⽪细胞": null,
"中毒颗粒⽩细胞": "未检出", "线索细胞": "未检出",
"真菌（孢⼦） ": "未检出",
"真菌（芽⽣孢⼦） ": "未检出", "真菌（假菌丝） ": "未检出",  "真菌（菌丝） ": "未检出",
"滴⾍": "未检出",
"衣原体（包涵体） ": "未检出", "阴道清洁度": "Ⅰ ",
"背景菌落": "不明显或溶胞性", "菌群密集度": "Ⅱ ",
"菌群多样性": "Ⅱ ",
"基底上⽪细胞比例": null, "线索细胞比例": null,
"含中毒颗粒⽩细胞比例": null },
{
"Id": "3a0e9bcc-560d-9ad1-18c5-fc2913fba003",
"姓名": null, "性别": "女", "年龄": "0",
"诊疗卡号": null, "样本编号": null, "床号": null,
"标本种类": "分泌物", "送检医师": null,
"送检科室": null,  "分泌物性状": null, "评价结论": null,  "采样时间": null,  "接收时间": null,
"报告时间": "2023-11-02 09:45",
"检验者": null,  "审核者": null,  "临床诊断": null,
"阴道分泌物pH值": null,
"Donders评分": null, "上⽪细胞": "-",
"⽩细胞": "0-5",  "乳杆菌": "++++", "杂菌": "+",
"基底上⽪细胞": null,
"中毒颗粒⽩细胞": "未检出", "线索细胞": "未检出",
"真菌（孢⼦） ": "未检出",
"真菌（芽⽣孢⼦） ": "未检出", "真菌（假菌丝） ": "未检出",  "真菌（菌丝） ": "未检出",
"滴⾍": "未检出",




返回参数说明

参数名             类型       说明
totalCount     int         总数
items              array     结果数组

备注: 所有返回的字段都以中文作为 key 返回. 由于此内容会依据不同医院动态调整, 所以具体的字段名称以医院 实际情况为准.
下载报告PDF文件
简要描述

.  获取报告PDF, 通过Id下载报告的Pdf

请求URL

·    http://127.0.0.1:9601/api/app/reports/pdf

请求⽅式

   GET

参数

参数名      必选      类型      说明
key           是         guid     报告Id

返回⽰例

直接返回⼆进制pdf
