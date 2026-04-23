一、STG数据质检需求

1.1 本文目的
尝试描述STG数据质检方案，以便AI能自动生成数据质检代码。

1.2 STG数据质检背景
每月月初报送时报表勾稽问题多时间紧，实施同学需要加班加点处理数据问题，比较痛苦。按经验至少一半的问题属于上游系统数据没及时维护，我们希望能提前发现并处置这些问题，比如当月月末做巡检发现问题及时补录，减少月初报送的压力。

1.3 报表系统数据分层介绍
数据层级	层级名称	分层说明
STG	贴源层	将业务系统的[原表/接口]数据落地至STG层，原则上不对数据进行任何加工，尽量保持跟业务系统的一致性，方便后续进行溯源。
DWD	数据明细层	DWD分为两类表：维度表和事实表。
1.维度表：
维度是逻辑概念，是衡量和观察业务的角度。
对于信托行业来说，主要的维度包括：
项目、产品、信托合同、信托客户、资管合同、交易对手、证券、账套...
维度表要按照【公共、产品、会计核算、参与者、投资品种、内部组织、资产、事件、协议、渠道、营销方式】分类。
需要注意的是：
维度层中，每个表都对应一个单独的维度。
2.事实表
发生在现实世界中的操作型事件，所产生的可度量数值，存储在事实表中。
简而言之，业务系统的流水表、持仓表，就是事实表。
任何数据的记录都可以从事实表获取，为后续的DWS层进行数据统计做准备。
事实表一般都集中在【事件】和【资产】域。
DWS	公共指标层	公共指标层按照主要数据维度和业务规则进行数据聚合； 
比如：TA申购金额、TA赎回金额。申购和赎回都是业务概念，不会随着报表需求而变化。
对于依据报送规则创建的指标，不在DWS层管理。
DWS层，一般在最低维度聚合，比如：【申购余额】，在合同、产品、项目都有，但是DWS只在合同维度聚合。
DM层根据报送的需求，在产品、项目层进行聚合。
DM	业务指标层	业务指标层按照报表需求，在DWS的基础上，对指标进行再次的加减和聚合。
比如：DWS层有指标：【合同.成立金额、合同.申购金额、合同.分红再投金额】；
在DM中，可以按照报表需求，将数据聚合至项目层，生成指标：【项目.成立金额、项目.申购金额、项目.分红再投金额】。
也可以将指标进行加减，生成新的复合指标：【项目.新增金额(成立+申购+分红再投)】。
RPT	业务报表层	报表报送用的所有数据，自使用系统时开始，应永久存储。

1.4 STG数据质检方案
从DM层向上游回溯（DM-->DWS(如果存在)->DW-->STG），找到DM层缺少数据在STG层对应的是哪笔数据，并且输出这笔数据的业务主键以及辅助信息。
这里先简单总结STG数据质检方案，后面会穷举可能的情形：
1、自上而下的查找，同模型清洗加工方向相反；
2、保证DM层与本期RPT报送相同的数据范围；
3、输出有问题的STG数据的业务主键（如果存在），方便定位是哪笔数据
4、输出辅助信息，包括字段名、表名、表来源系统、字段在业务系统路径等技术辅助字段以及该笔数据所属的项目代码、项目名称、项目经理以及项目经理所属部门等业务辅助信息（如果存在），详见2.5节。
说明：以上描述括号中“如果存在”说明只是一般情况，实际存在特殊情况。


1.5 STG数据质检例子
假设定期报送DQ01产品基本信息表勾稽：
 勾稽代码：DQ01.A0007	
 勾稽说明：<产品基本信息表-项目运作模式>不应为空
 勾稽描述：项目代码XX，项目名称XX的项目运作模式为空！
 报表名称：URP_SRDT5_CPJBXXB （项目信息表）
 报表字段：XMYZMS（项目运作方式）
项目信息表可能有多个来源系统，常见是恒生的TCMP系统，也有从外部系统（非恒生系统通用叫法）来的，假设项目是从TCMP来，STG数据质检代码为：
 select distinct  
       '<产品基本信息表-项目运作模式>不应为空' check_name, --勾稽名称
       /*以下技术辅助字段*/
       'T2_TCMP_PROJECTINFO' stg_table_name, --STG表名
       '项目信息' stg_table_name_cn, --STG表中文名
       'RUN_TYPE' stg_col_name, --STG字段名
       '运行方式' stg_col_name_cn, 	  --STG字段中文名	   
        RUN_TYPE stg_col_value, --字段取值
       '项目编号['||project_code||'],项目名称['||project_name||']' stg_key, --业务主键
       /*以下业务辅助字段*/
       proj.count_proj_code,
       proj.count_proj_name, 
       urp3_xtdw.fn_company_dict(proj.trust_manager, '1') trust_manager, --信托经理
       urp3_xtdw.fn_company_dict(proj.deal_manage, '1') deal_manage,     --运营经理
       urp3_xtdw.fn_company_dict(proj.trust_manager_b, '1') trust_manager_b, --信托经理B
       urp3_xtdw.fn_company_dict(proj.trust_manager_c, '1') trust_manager_c, --信托经理C	   
       urp3_xtdw.fn_company_dict(proj.beit_dept, '2') beit_dept,         --所属部门
	   /*以下是报送标识*/
       k.report_flag_tprt, --定期报送标识
	   k.report_flag_east5 --EAST5标识标识
from  urp3_tusp.dm_ctrc_cpjbxxzbb k --DM层项目信息表
inner join urp3_xtdw.dw_d_count_proj_info proj --DW层项目信息表
    on k.count_proj_code = proj.count_proj_code --关联条件
   and proj.data_source='TCMP' --限制DW表的项目是从TCMP系统来的
inner join urp3_xtstg.t2_tcmp_projectinfo t --STG层项目信息表
	on proj.proj_code = t.project_code  --关联条件
where k.cal_date = 20260228 --限制报送期次为2026年2月报送 
and (k.report_flag_tprt = '1' or k.report_flag_east5 = '1') --只回溯定期报送和EAST5报送的数据 
and  proj.busi_scope = '1'  --1表示信托业务，固定限制条件
and  trim(k.xmyzms) is null  --dm表项目运作模式为空，有问题的数据

1.6 输出格式
字段名				字段中文名            说明
---------          -------------         ----------
check_name			勾稽名称             勾稽描述：比如<产品基本信息表-项目运作模式>不应为空
stg_table_name		STG表名				 技术辅助字段
stg_table_name_cn   STG表中文名          技术辅助字段
stg_col_name		STG字段名            技术辅助字段
stg_col_name_cn     STG字段中文名        技术辅助字段
stg_col_value		字段取值             技术辅助字段
stg_key				业务主键             技术辅助字段
count_proj_code		项目代码             业务辅助字段
count_proj_code		项目名称             业务辅助字段
trust_manager		信托经理             业务辅助字段
deal_manage			运营经理             业务辅助字段
beit_dept			所属部门             业务辅助字段
report_flag_tprt	定期报送标识         报送标识
report_flag_east5	EAST5标识标识        报送标识


二、STG数据质检代码满足如下规范

2.1 一致性检查
2.1.1巡检表或字段一致检查
测试案例名称：巡检表或者字段不在SQL中的情形
测试案例说明：确保SQL规则与辅助信息一致 
测试案例代码：
select t.check_code,t.check_name,'2.1.1巡检表或字段一致检查' as tips --,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t  
where instr(upper(to_char(check_sql)),t.stg_table_name)=0
or instr(upper(to_char(check_sql)),t.stg_table_col_name)=0

2.1.2表名与接口文档一致检查
测试案例名称：巡检表名与接口文档不一致的情形
测试案例说明： 确保表名与接口文档一致
测试案例代码：
select  t.check_code,
        t.stg_table_col_name,
        --t1.c_filecode,
        t.stg_tabl_name_ch STG表中文名,
        t1.c_tabname 接口表中文名,
        t.stg_table_col_name_ch STG字段中文名,
        t1.c_filename 接口字段中文名,
        case when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename then '1=表中文名和字段中文名都不相同'
             when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch =t1.c_filename  then '2=表中文名不相同'
             when  t.stg_tabl_name_ch = t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename  then '3=字段中文名不相同'
             else '4-其他情况' end remark, 
        '2.1.2表名与接口文档一致检查（TCMP）' as tips --,t.*          
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_tcmp t1
on t.stg_table_name = t1.c_tabcode
where 1=1
and upper(t.stg_table_col_name) =upper(t1.c_filecode)
and( t.stg_tabl_name_ch <> t1.c_tabname 
 or t.stg_table_col_name_ch <>t1.c_filename
)
union all
select  
        t.check_code,
        t.stg_table_col_name,
        --t1.c_filecode,
        t.stg_tabl_name_ch STG表中文名,
        t1.c_tabname 接口表中文名,
        t.stg_table_col_name_ch STG字段中文名,
        t1.c_filename 接口字段中文名,
        case when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename then '1=表中文名和字段中文名都不相同'
             when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch =t1.c_filename  then '2=表中文名不相同'
             when  t.stg_tabl_name_ch = t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename  then '3=字段中文名不相同'
             else '4-其他情况' end remark,         
        '2.1.2表名与接口文档一致检查（TA）' as tips --,t.*     
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_ta t1
on t.stg_table_name = t1.c_tabcode
where 1=1
and upper(t.stg_table_col_name) =upper(t1.c_filecode)
and (t.stg_tabl_name_ch <>t1.c_tabname 
  or  t.stg_table_col_name_ch <>t1.c_filename
)
union all
select  
        t.check_code,
        t.stg_table_col_name,
        --t1.c_filecode,
        t.stg_tabl_name_ch STG表中文名,
        t1.c_tabname 接口表中文名,
        t.stg_table_col_name_ch STG字段中文名,
        t1.c_filename 接口字段中文名,
        case when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename then '1=表中文名和字段中文名都不相同'
             when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch =t1.c_filename  then '2=表中文名不相同'
             when  t.stg_tabl_name_ch = t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename  then '3=字段中文名不相同'
             else '4-其他情况' end remark,         
        '2.1.2表名与接口文档一致检查（AM）' as tips --,t.*    
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_am t1
on t.stg_table_name = t1.c_tabcode
where 1=1
and upper(t.stg_table_col_name) =upper(t1.c_filecode)
and( t.stg_tabl_name_ch <> t1.c_tabname 
 or t.stg_table_col_name_ch <>t1.c_filename
)

2.1.3字段路径截图命名一致性检查
测试案例名称：巡检字段截图命名不符合规范的情形
测试案例说明： 确保字段截图命名正确
测试案例代码：
select  t.check_code,
        t.stg_table_col_name,
        --t1.c_filecode,
        t.stg_tabl_name_ch STG表中文名,
        t1.c_tabname 接口表中文名,
        t.stg_table_col_name_ch STG字段中文名,
        t1.c_filename 接口字段中文名,
        case when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename then '1=表中文名和字段中文名都不相同'
             when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch =t1.c_filename  then '2=表中文名不相同'
             when  t.stg_tabl_name_ch = t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename  then '3=字段中文名不相同'
             else '4-其他情况' end remark, 
        '2.1.2表名与接口文档一致检查（TCMP）' as tips --,t.*          
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_tcmp t1
on t.stg_table_name = t1.c_tabcode
where 1=1
and upper(t.stg_table_col_name) =upper(t1.c_filecode)
and( t.stg_tabl_name_ch <> t1.c_tabname 
 or t.stg_table_col_name_ch <>t1.c_filename
)
union all
select  
        t.check_code,
        t.stg_table_col_name,
        --t1.c_filecode,
        t.stg_tabl_name_ch STG表中文名,
        t1.c_tabname 接口表中文名,
        t.stg_table_col_name_ch STG字段中文名,
        t1.c_filename 接口字段中文名,
        case when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename then '1=表中文名和字段中文名都不相同'
             when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch =t1.c_filename  then '2=表中文名不相同'
             when  t.stg_tabl_name_ch = t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename  then '3=字段中文名不相同'
             else '4-其他情况' end remark,         
        '2.1.2表名与接口文档一致检查（TA）' as tips --,t.*     
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_ta t1
on t.stg_table_name = t1.c_tabcode
where 1=1
and upper(t.stg_table_col_name) =upper(t1.c_filecode)
and (t.stg_tabl_name_ch <>t1.c_tabname 
  or  t.stg_table_col_name_ch <>t1.c_filename
)
union all
select  
        t.check_code,
        t.stg_table_col_name,
        --t1.c_filecode,
        t.stg_tabl_name_ch STG表中文名,
        t1.c_tabname 接口表中文名,
        t.stg_table_col_name_ch STG字段中文名,
        t1.c_filename 接口字段中文名,
        case when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename then '1=表中文名和字段中文名都不相同'
             when  t.stg_tabl_name_ch <> t1.c_tabname and t.stg_table_col_name_ch =t1.c_filename  then '2=表中文名不相同'
             when  t.stg_tabl_name_ch = t1.c_tabname and t.stg_table_col_name_ch <>t1.c_filename  then '3=字段中文名不相同'
             else '4-其他情况' end remark,         
        '2.1.2表名与接口文档一致检查（AM）' as tips --,t.*    
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_am t1
on t.stg_table_name = t1.c_tabcode
where 1=1
and upper(t.stg_table_col_name) =upper(t1.c_filecode)
and( t.stg_tabl_name_ch <> t1.c_tabname 
 or t.stg_table_col_name_ch <>t1.c_filename
)

2.1.4描述一致检查
测试案例名称：巡检描述和规则不一致的情形
测试案例说明：确保描述与巡检规则一致 
测试案例代码：
select t.check_code,t.check_name,'2.1.4描述一致检查' as tips --,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t 
where instr(upper(to_char(check_sql)) ,check_name)=0

2.1.5大小写一致检查
测试案例名称：表名或者字段名大小写不一致的情形
测试案例说明： 确保巡检输出信息规范
测试案例代码：
select t.check_code,t.check_name,'2.1.5大小写一致检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t
where upper(stg_table_name) <> stg_table_name
   or upper(stg_table_col_name) <> stg_table_col_name

2.1.6报表勾稽代码一致检查
测试案例名称：巡检中引用的报表勾稽代码不存在的情形
测试案例说明： 确保报表勾稽代码存在
测试案例代码：
select t.check_code,t.check_name,'2.1.6报表勾稽代码一致检查' as tips --,t.*   
from urp3_tusp.URP_STG_DATA_CHECK t 
where replace(check_code_urp ,chr(10),'') not in 
  (select check_code from URP_DATACHECK_RULE t
  where t.parent_module_code like 'TPRT%' 
  or t.parent_module_code like 'EAST50%'
  or t.parent_module_code like 'TPRP%'
   or t.parent_module_code like 'XTPBOCZG2024.ZG%')
and check_code_urp not like 'NB%'
and check_code_urp not like 'XT.NB%'

2.1.7报表701~705剔除互联网贷款检查
测试案例名称：巡检701~705报表没有剔除互联网贷款的情形
测试案例说明： 确保逻辑一致性
测试案例代码：
select t.check_code,t.check_name,'2.1.7报表701~705剔除互联网贷款检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t 
where regexp_like(t.check_code_urp,'701.|702.|703.|704.|705.')  
  and not regexp_like(upper(check_sql), '.*DM_CTRC_CPTZZBB.*SFHLWDK.*', 'n' )
order by  t.check_code

2.1.8交易对手限制客户类型检查
测试案例名称：巡检EAST5交易对手没有限制客户类型的情形
测试案例说明：确保逻辑一致性
测试案例代码：
select t.check_code,t.check_name,'2.1.8交易对手限制客户类型检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t 
where ( regexp_like(t.check_code_urp,'^204.') and not regexp_like(regexp_replace(upper(check_sql),'\s',''),q'[CPY_TYPE='1']') )
  or  ( regexp_like(t.check_code_urp,'^205.') and not regexp_like(regexp_replace(upper(check_sql),'\s',''),q'[CPY_TYPE='2']') )
  or  ( regexp_like(t.check_code_urp,'^206.') and not regexp_like(regexp_replace(upper(check_sql),'\s',''),q'[CPY_TYPE='3']') )

2.1.9报表701~705业务类型一致性检查
测试案例名称：巡检701~705报表业务分类和清洗逻辑不一致的情形
测试案例说明：确保逻辑一致性
测试案例代码：
select t.check_code,t.check_name,'2.1.9报表701~705业务类型一致性检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t 
where regexp_like(t.check_code_urp,'701.|702.|703.|704.|705.')
 and regexp_replace(upper(check_sql),'\s') not like '%XTYWFLIN(''1'',''3'')%ZCFWXTFL1IN(''0'',''4'')%ZCFWXTFL2=''11''%'
order by  t.check_code

2.1.10是否互联网贷款业务类型一致性检查
测试案例名称：是否互联网贷款业务分类和清洗逻辑不一致的情形
测试案例说明：确保逻辑一致性
测试案例代码：
select t.check_code,t.check_name,'2.1.10是否互联网贷款业务类型一致性检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t 
where regexp_like(regexp_replace(t.check_name, '\s"') ,'<产品特征表-是否互联网贷款>选择是时')
 and regexp_replace(upper(check_sql),'\s') not like '%XTYWFLIN(''0'',''1'',''3'')%'
order by  t.check_code

2.1.11资产取得方式选择资金投向一致性检查
测试案例名称：资产取得方式选择资金投向和清洗逻辑不一致的情形
测试案例说明：确保逻辑一致性
测试案例代码：
select  t.check_code,t.check_name,'2.1.11资产取得方式选择资金投向一致性检查' as tips --,t.*   
from urp3_tusp.URP_STG_DATA_CHECK t 
where regexp_like(regexp_replace(check_name,'[\s"]'), '资产取得方式>选择资金投向时') 
and not regexp_like(regexp_replace(upper(check_sql),'\s') ,  q'[ZCQDFS='0'|ZCQDFSIN\('0'\)|ZCQDFS,'0']')
order by t.check_code

2.1.12反之必填一致性检查
测试案例名称：反之必填没有实现的情形
测试案例说明：确保描述和实现一致性
测试案例代码：
select  t.check_code,t.check_name,'2.1.12反之必填一致性检查' as tips --,t.*   
from urp3_tusp.URP_STG_DATA_CHECK t 
where check_name like '%反之不应填写%'
order by t.check_code

2.1.13规则表字段与输出一致性检查
测试案例名称：规则表字段和输出不一致的情形
测试案例说明：确保规则表和输出是一致性
测试案例代码：
select  t.check_code,t.check_name,'2.1.13规则表字段与输出一致性检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t
where instr(upper(to_char(check_sql)),upper(stg_tabl_name_ch))=0
or instr(upper(to_char(check_sql)),upper(stg_table_col_name_ch))=0
order by t.check_code

2.1.14关联方信息表参数限制一致性检查
测试案例名称：关联方信息表参数不一致的情形
测试案例说明：确保关联方信息表参数和清洗逻辑是一致
测试案例代码：
select  t.check_code,t.check_name,'2.1.14关联方信息表参数限制一致性检查' as tips --,t.*  
from urp3_tusp.URP_STG_DATA_CHECK t
where check_name like '%<关联方信息表-%>%'
 and upper(check_sql) not like '%URP_PARAM_CONFIG%SRDT5_GLFXXBQSLY%'
order by t.check_code

2.1.15巡检描述与报表勾稽描述一致性检查
测试案例名称：巡检描述与报表勾稽描述不一致的情形
测试案例说明：确保巡检描述与报表勾稽描述一致
测试案例代码：
select  t.check_code,t.check_name,'2.1.15巡检描述与报表勾稽描述一致性检查' as tips --,t.*    
from urp3_tusp.URP_STG_DATA_CHECK t inner join URP_DATACHECK_RULE t1 on t.check_code_urp=t1.check_code
where  --check_code in ('SUC0834','SUC0835')
rely_version ='URP3.0.V202502.13.000'
and replace(t.check_name,'"','') <>replace(t1.check_name,'"','')

2.2 简洁性检查
2.2.1巡检代码逻辑重复勾稽检查
测试案例名称：SQL内容重复勾稽的情形
测试案例说明： 确保巡检勾稽无冗余
测试案例代码：
select t.check_code,t.check_name, '2.2.1巡检代码逻辑重复勾稽检查' as tips --报表勾稽有重复的勾稽代码逻辑
from urp3_tusp.URP_STG_DATA_CHECK t 
join (select upper(to_char(check_sql)) check_sql,row_number() over(order by 1) rn
    from urp3_tusp.URP_STG_DATA_CHECK t
    group by to_char(check_sql)
    having count(1)>1
    ) t2
on  regexp_replace(upper(to_char(t.check_sql)),'\s')=regexp_replace(t2.check_sql, '\s') --删除空格后匹配

2.2.2勾稽代码重复检查
测试案例名称：勾稽代码有重复的情形
测试案例说明：确保巡检勾稽代码唯一
测试案例代码：
select check_code,'' check_name, '2.2.2勾稽代码重复检查' as tips--,t.*
from urp3_tusp.URP_STG_DATA_CHECK t
group by check_code
having count(1)>1

2.2.3勾稽代码限制条件重复
测试案例名称：勾稽代码中限制条件有重复情形
测试案例说明：确保巡检代码简洁无冗余
测试案例代码：
先人工判断，SQL判断代码的限制条件比较麻烦

2.2.4勾稽代码关联表重复
测试案例名称：勾稽代码中关联表有重复情形
测试案例说明：确保巡检代码简洁无冗余
测试案例代码：
先人工判断，SQL判断代码的限制条件比较麻烦

2.3 完整性检查
2.3.1中文名为空检查
测试案例名称：表中文名或者字段中文名为空的情形
测试案例说明： 确保巡检输出信息完整
测试案例代码：
select check_code,check_name, '2.3.1中文名为空检查' as tips, t.*
from urp3_tusp.URP_STG_DATA_CHECK t  
where ((stg_table_name is not null and stg_tabl_name_ch is null) 
or (stg_table_name is not null and stg_tabl_name_ch = '0') 
or (stg_table_col_name is not null and stg_table_col_name_ch is null)
or (stg_table_col_name is not null and stg_table_col_name_ch = '0')) 
--and  check_code_urp not like 'NB.%' 

2.3.2字段路径存在检查
测试案例名称：巡检字段路径遗漏的情形
测试案例说明： 确保字段路径完整
测试案例代码：
select check_code, check_name, '2.3.2字段路径存在检查(TCMP)' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_tcmp t1
  on t.stg_table_name = t1.c_tabcode
  and upper(t.stg_table_col_name) =upper(t1.c_filecode)
where nvl(replace(replace(t.stg_col_path,chr(13),''),chr(10),''),'#') <> nvl(replace(replace(replace(c_path,'"',''),chr(13),''),chr(10),''),'$')
  and nvl(c_path,' ')<>' ' --排除接口文档路径为空的情况
union all 
select check_code, check_name, '2.3.2字段路径存在检查(非标)' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t
inner join TEST_FILE_AM t1
  on t.stg_table_name = t1.c_tabcode
  and upper(t.stg_table_col_name) =upper(t1.c_filecode)
where (
replace(replace(replace(replace(replace(replace(t.stg_col_path,chr(13),''),chr(10),''),' ',''),'"',''),'。',''),'“','') <> 
replace(replace(replace(replace(replace(replace(replace('AIMS：'||c_path_aims||'；'||'AM1.0：'||c_path_am,'"',''),chr(13),''),chr(10),''),' ',''),'"',''),'。',''),'“','')
)
and not(nvl(c_path_aims,' ')=' ' and nvl(c_path_am,' ')=' ') --排除接口文档为空的情况
and not(c_path_aims like '%T22026%' and c_path_am like '%T22026%') 
union all 
select check_code, check_name, '2.3.2字段路径存在检查(TA)' as tips --,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t
inner join test_file_ta t1
  on t.stg_table_name = t1.c_tabcode
  and upper(t.stg_table_col_name) =upper(t1.c_filecode)
where nvl(replace(replace(t.stg_col_path,chr(13),''),chr(10),''),'#')<>nvl(replace(replace(replace(c_path,'"',''),chr(13),''),chr(10),''),'$')
and not(nvl(c_path,' ')=' ')

2.3.3字段路径是否一致
测试案例名称：字段路径不完整的情形
测试案例说明： 确保字段格式完整
测试案例代码：
select check_code, check_name, '2.3.3字段路径是否一致' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t
where regexp_like(REGEXP_SUBSTR(stg_col_src_pic,'^[^.]+') ,'^_|_$' ) --以下划线开头或者结尾的路径

2.3.4巡检代码未实现检查
测试案例名称：巡检代码中输出字段没有实现逻辑的情形
测试案例说明： 确保巡检代码中输出字段有取值
测试案例代码：
select check_sql, check_code, check_name, '2.3.4巡检代码未实现检查' as tips --,t.*
from urp3_tusp.URP_STG_DATA_CHECK t 
where regexp_like(regexp_replace(upper(check_sql),'\s',''),       q'[''STG_COL_NAME|''ASSTG_COL_NAME|''STG_COL_VALUE|''ASSTG_COL_VALUE]') --1.先用regexp_replace删除空格、制表符、换行符、回车符、换页符等
  --2. 再用regexp_like检查是否包含''STG_COL_NAME或''ASSTG_COL_NAME或''STG_COL_VALUE或''ASSTG_COL_VALUE

2.3.5巡检代码报送标识检查
测试案例名称：巡检代码中输出列未包含报送标识的情形
测试案例说明： 确保巡检代码中输出报送标识
测试案例代码：
select check_code, check_name, '2.3.5巡检代码报送标识检查' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t 
where check_code_urp not like 'NB.%' 
and (instr( upper(to_char(check_sql)),'REPORT_FLAG_EAST5')=0 
   or instr( upper(to_char(check_sql)),'REPORT_FLAG_TPRT')=0)

2.3.6巡检代码输出列表不全检查
测试案例名称：巡检代码中输出列表不完整的情形
测试案例说明： 确保巡检代码中输出完整
测试案例代码：
select check_code_urp, check_sql, check_code, check_name, '2.3.6巡检代码输出列表检查' as tips --,t.*
from urp3_tusp.URP_STG_DATA_CHECK t 
where  not regexp_like(check_code_urp,'^(101\.|102\.|103\.|104\.|313\.|DQ28\.|DQ36\.|NB\.)')  --排除 员工信息表、 关联方信息表、关联交易、内部自定义勾稽等与项目无关的报表 后面发现有需要新排查的报表在排除列表中增加
   and not (upper(check_sql) like '%PROJ.COUNT_PROJ_CODE%PROJ.COUNT_PROJ_NAME%PROJ.TRUST_MANAGER%PROJ.TRUST_MANAGER_B%PROJ.TRUST_MANAGER_C%PROJ.DEAL_MANAGE%PROJ.BEIT_DEPT%'
       or upper(check_sql) like '%K.COUNT_PROJ_CODE%%K.COUNT_PROJ_NAME%%K.TRUST_MANAGER%%K.TRUST_MANAGER_B%%K.TRUST_MANAGER_C%%K.DEAL_MANAGE%%K.BEIT_DEPT%'
       ) --没有完整输出项目信息

2.4 其他情形检查
2.4.1巡检代码结尾检查
测试案例名称：巡检SQL结尾是否有分号的情形
测试案例说明：确保SQL能正确执行 
测试案例代码：
select t.check_sql,t.*,t.rowid from urp3_tusp.URP_STG_DATA_CHECK t 
where  t.check_sql  like '%;' 

2.4.2业务日期写死检查
测试案例名称：写死业务日期的情形
测试案例说明：确保业务日期参数提替换 
测试案例代码：
select check_sql, check_code, check_name, '2.4.1巡检代码结尾检查' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t 
Where regexp_like(t.check_sql,'[12][0-9]{7}') --8位数字，第1位是1和2，第2~7位是0-9

2.4.3代码空格检查
测试案例名称：代码存在空行的情形
测试案例说明： 确保代码文本规范
测试案例代码：
select check_code, check_name, '2.4.3代码空格检查' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t 
where (t.stg_table_name like 'T2%' or t.stg_table_name like 'TS%')
and (
    check_sql is null  -- 检查是否为NULL
    or DBMS_LOB.GETLENGTH(check_sql) = 0  -- 检查长度是否为0
    or DBMS_LOB.SUBSTR(check_sql, 1) is null  -- 检查是否可以读取内容
    or (
        -- 检查是否只包含空白字符（只检查前4000字符）
        REGEXP_LIKE(DBMS_LOB.SUBSTR(check_sql, 4000, 1), '^\s*$', 'm')
        and DBMS_LOB.GETLENGTH(check_sql) <= 4000  -- 确保CLOB不超过4000字符
    )
)


2.4.4巡检代码文本长度检查
测试案例名称：SQL文本超长的情形
测试案例说明： 确保检查SQL文本检查函数能有效执行
测试案例代码：
select check_code, check_name, '2.4.4巡检代码文本长度检查' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t
where length(check_sql) > 3900; --文本超过3900后导致to_char等函数无法执行

2.4.5提测批次检查
测试案例名称：巡检勾稽批次漏提或者错提的情形
测试案例说明： 确保提交批次正确
测试案例代码：
select RELY_VERSION ,
      VERSION_BATCH,
count(1) as num
from urp3_tusp.URP_STG_DATA_CHECK t
group by RELY_VERSION,VERSION_BATCH
order by 1;

2.4.6巡检路径换行检查
测试案例名称：巡检AIMS/AM1勾稽路径没有换行的情形
测试案例说明： 确保界面分行显示
测试案例代码：
select check_code, check_name, '2.4.6巡检路径换行检查' as tips--,t.* 
from urp3_tusp.URP_STG_DATA_CHECK t
where  stg_col_path like '%AIMS%AM%'
     and not regexp_like(stg_col_path,'[' || CHR(10) || CHR(13) || ']')