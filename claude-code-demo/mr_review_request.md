================================================================================
GitLab MR 代码评审请求
================================================================================

## MR 信息

- **URL**: https://git.cai-inc.com/rdc/paas/shareservice/expert-server/-/merge_requests/139
- **标题**: Release/expert jc 20251220
- **描述**: (无)
- **源分支**: release/expert_jc_20251220
- **目标分支**: master
- **Source Commit**: c507aea7f967359e1682e23f8f6144f25270b51b
- **Target Commit**: e44958bfa26f835add77a3f7bdfa092bd15895d4

## 变更文件 (44 个)

1. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/component/BidAreaBusinesComponent.java`

```diff
@@ -1,26 +1,23 @@
 package cn.gov.zcy.experts.component;
 
+import cn.gov.zcy.common.api.Response;
 import cn.gov.zcy.experts.config.ExpertCommonConfig;
-import cn.gov.zcy.experts.dao.BidAreaDao;
-import cn.gov.zcy.experts.dao.BidMutuallyDao;
-import cn.gov.zcy.experts.dao.ExpertJobBidRelationDAO;
-import cn.gov.zcy.experts.dao.ExpertsBidCustomDao;
-import cn.gov.zcy.experts.dao.ExpertsBidareaTempDao;
-import cn.gov.zcy.experts.dao.LibraryInfoDao;
-import cn.gov.zcy.experts.domain.BidArea;
-import cn.gov.zcy.experts.domain.BidMutuallyDomain;
-import cn.gov.zcy.experts.domain.ExpertJobBidRelationDO;
-import cn.gov.zcy.experts.domain.ExpertsBidCustom;
-import cn.gov.zcy.experts.domain.ExpertsBidareaTemp;
-import cn.gov.zcy.experts.domain.LibraryInfoDomain;
+import cn.gov.zcy.experts.dao.*;
+import cn.gov.zcy.experts.domain.*;
 import cn.gov.zcy.experts.dto.ExpertsBidAreaDto;
+import cn.gov.zcy.experts.dto.ExpertsLibraryRuleConfigExtFieldsDTO;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigReqDTO;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigResponseDTO;
 import cn.gov.zcy.experts.dto.library.LibraryDto;
+import cn.gov.zcy.experts.enums.LibraryTypeEnum;
 import cn.gov.zcy.experts.enums.YesNoEnum;
 import cn.gov.zcy.experts.query.ExpertJobBidRelationQuery;
+import cn.gov.zcy.experts.service.ExpertSettleReadService;
 import cn.gov.zcy.experts.service.LibraryReadService;
 import cn.gov.zcy.experts.util.OptimizationBeanTools;
 import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
 import com.baomidou.mybatisplus.core.toolkit.Wrappers;
+import com.fasterxml.jackson.databind.ObjectMapper;
 import com.google.common.collect.Lists;
 import com.google.common.collect.Maps;
 import lombok.extern.slf4j.Slf4j;
@@ -31,13 +28,7 @@ import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.context.annotation.Lazy;
 import org.springframework.stereotype.Component;
 
-import java.util.ArrayList;
-import java.util.Arrays;
-import java.util.Collections;
-import java.util.HashMap;
-import java.util.List;
-import java.util.Map;
-import java.util.Optional;
+import java.util.*;
 import java.util.concurrent.atomic.AtomicReference;
 import java.util.stream.Collectors;
 
@@ -74,6 +65,12 @@ public class BidAreaBusinesComponent {
     private ExpertJobBidRelationDAO expertJobBidRelationDAO;
     @Autowired
     private ExpertCommonConfig expertCommonConfig;
+    @Autowired
+    private ExpertSettleReadService expertSettleReadService;
+    @Autowired
+    private BigLibraryDao bigLibraryDao;
+    @Autowired
+    private LibraryRuleDao libraryRuleDao;
 
     /**
      * 获取所有专业元数据
@@ -151,6 +148,11 @@ public class BidAreaBusinesComponent {
             }
         }
         cond.setStatus(status);
+        //查询依赖库，如果有依赖库，使用依赖库的专业
+        String dependenceInstanceCode = getDependenceInstanceCode(instanceCode);
+        if (StringUtils.isNotEmpty(dependenceInstanceCode)) {
+            instanceCode = dependenceInstanceCode;
+        }
         ExpertsBidCustom bidCustom = expertsBidCustomDao.getPublishCustomByInstanceCode(instanceCode);
         if (null == bidCustom) {
             return filterBidArea(list, instanceCode == null ? null : Collections.singletonList(instanceCode));
@@ -171,7 +173,11 @@ public class BidAreaBusinesComponent {
         if (instanceCode == null) {
             return commonBidAreas;
         }
-
+        //查询依赖库，如果有依赖库，使用依赖库的专业
+        String dependenceInstanceCode = getDependenceInstanceCode(instanceCode);
+        if (StringUtils.isNotEmpty(dependenceInstanceCode)) {
+            instanceCode = dependenceInstanceCode;
+        }
         ExpertsBidCustom publishConfig =
                 expertsBidCustomDao.getPublishCustomByInstanceCode(instanceCode);
 
@@ -242,7 +248,11 @@ public class BidAreaBusinesComponent {
             }
             instanceCode = libraryInfo.getInstanceCode();
         }
-
+        //查询依赖库，如果有依赖库，使用依赖库的专业
+        String dependenceInstanceCode = getDependenceInstanceCode(instanceCode);
+        if (StringUtils.isNotEmpty(dependenceInstanceCode)) {
+            instanceCode = dependenceInstanceCode;
+        }
         // >> 1、newCustomId > 0 用于处理原来有旧的专业树（共用专业树除外），现在有新的专业树的情况
         // >> 2、publishStatus == 0 && isTrial == 1 是为了查询之前使用共用专业树，现在使用自定义专业树的情况
         ExpertsBidCustom queryBidCustom = new ExpertsBidCustom();
@@ -318,7 +328,18 @@ public class BidAreaBusinesComponent {
         if (CollectionUtils.isEmpty(libraryDtos)) {
             return list;
         }
-        List<String> instanceCodes = libraryDtos.stream().map(p -> p.getInstanceCode()).collect(Collectors.toList());
+        List<String> instanceCodes = libraryDtos.stream().map(LibraryDto::getInstanceCode).collect(Collectors.toList());
+        List<String> dependenceInstanceCodes = new ArrayList<>();
+        instanceCodes.forEach(p -> {
+            //查询依赖库，如果有依赖库，使用依赖库的专业
+            String dependenceInstanceCode = getDependenceInstanceCode(p);
+            if (StringUtils.isNotEmpty(dependenceInstanceCode)) {
+                dependenceInstanceCodes.add(dependenceInstanceCode);
+            }else {
+                dependenceInstanceCodes.add(p);
+            }
+        });
+        instanceCodes = dependenceInstanceCodes;
         List<ExpertsBidCustom> bidCustoms = expertsBidCustomDao.selectList(new LambdaQueryWrapper<ExpertsBidCustom>().
                 in(ExpertsBidCustom::getInstanceCode, instanceCodes).eq(ExpertsBidCustom::getIsTrial, YesNoEnum.NO.getCode()).
                 eq(ExpertsBidCustom::getIsDelete, 0));
@@ -699,6 +720,37 @@ public class BidAreaBusinesComponent {
         return String.join(",", bidDetails);
     }
 
+    /**
+     * 查询依赖库code
+     */
+    public String getDependenceInstanceCode(String instanceCode) {
+        // 只传 instanceCode，查询大库规则
+        BigLibraryDomain big = bigLibraryDao.selectOne(Wrappers.<BigLibraryDomain>lambdaQuery()
+                .eq(BigLibraryDomain::getInstanceCode, instanceCode)
+                .eq(BigLibraryDomain::getIsDelete, YesNoEnum.NO.getCode()));
+       if (Objects.nonNull(big)){
+           LibraryRuleDomain ruleDomain = libraryRuleDao.selectOne(Wrappers.<LibraryRuleDomain>lambdaQuery()
+                   .eq(LibraryRuleDomain::getLibraryId, big.getId())
+                   .eq(LibraryRuleDomain::getRuleType, LibraryTypeEnum.BIG.getCode())
+                   .eq(LibraryRuleDomain::getIsDelete, YesNoEnum.NO.getCode()));
+              if (Objects.nonNull(ruleDomain) && StringUtils.isNotEmpty(ruleDomain.getConfigExtFields())) {
+                  ExpertsLibraryRuleConfigExtFieldsDTO extDto;
+                  try {
+                      ObjectMapper mapper = new ObjectMapper();
+                      extDto = mapper.readValue(ruleDomain.getConfigExtFields(), ExpertsLibraryRuleConfigExtFieldsDTO.class);
+                      if (Objects.nonNull(extDto)) {
+                          return extDto.getDependingBigLibraryCode();
+                      }
+                  } catch (Exception e) {
+                      log.error("解析规则配置信息失败 ruleDomain:{}", ruleDomain.getConfigExtFields(), e);
+                      return null;
+                  }
+              }
+       }
+        return null;
+    }
+
+
     public static void main(String[] args) {
         String oldBidId = "1";
         List<Long> addBids = Arrays.asList(1L, 4L);

```

2. 🟢 新增 `experts-general/src/main/java/cn/gov/zcy/experts/component/ExpertDependedInfoComponent.java`
3. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/dao/OtherMaterialDao.java`

```diff
@@ -35,4 +35,5 @@ public interface OtherMaterialDao extends BaseMapper<OtherMaterialDomain> {
 
     int updateById(OtherMaterialDomain otherMaterialDomain);
 
+    void insertList(List<OtherMaterialDomain> otherMaterialDomains);
 }

```

4. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/dao/OtherMaterialFormalDao.java`

```diff
@@ -24,5 +24,7 @@ public interface OtherMaterialFormalDao extends BaseMapper<OtherMaterialFormalDo
 
     void copyNonKeyToFormal(List<OtherMaterialControl> list);
 
-    List<OtherMaterialFormalDomain> list(Long id);
+    List<OtherMaterialFormalDomain> list(Long libraryId);
+
+    void insertList(List<OtherMaterialFormalDomain> otherMaterialFormalDomainList);
 }

```

5. 🟢 新增 `experts-general/src/main/java/cn/gov/zcy/experts/dto/ExpertsLibraryRuleConfigExtFieldsDTO.java`

```diff
@@ -0,0 +1,51 @@
+package cn.gov.zcy.experts.dto;
+
+import lombok.Data;
+
+import java.io.Serializable;
+
+@Data
+public class ExpertsLibraryRuleConfigExtFieldsDTO implements Serializable {
+
+    private static final long serialVersionUID = -4066405037007693281L;
+
+    /**
+     * 依赖大库code
+     */
+    private String dependingBigLibraryCode;
+
+    /**
+     * 依赖大库name
+     */
+    private String dependingBigLibraryName;
+
+    /**
+     * 依赖子库code
+     */
+    private String dependingSubLibraryCode;
+
+    /**
+     * 依赖子库name
+     */
+    private String dependingSubLibraryName;
+
+    /**
+     * 被依赖大库code
+     */
+    private String dependedBigLibraryCode;
+
+    /**
+     * 依赖大库name
+     */
+    private String dependedBigLibraryName;
+
+    /**
+     * 被依赖子库code
+     */
+    private String dependedSubLibraryCode;
+
+    /**
+     * 被依赖子库name
+     */
+    private String dependedSubLibraryName;
+}

```

6. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/manage/settle/ExpertSettleWriteManage.java`

```diff
@@ -1,5 +1,6 @@
 package cn.gov.zcy.experts.manage.settle;
 
+import cn.gov.zcy.common.api.Response;
 import cn.gov.zcy.experts.component.*;
 import cn.gov.zcy.experts.config.CloudAndlandConfig;
 import cn.gov.zcy.experts.dao.*;
@@ -12,18 +13,14 @@ import cn.gov.zcy.experts.domain.renewal.ExpertIntentionDomain;
 import cn.gov.zcy.experts.domain.renewal.ExpertRenewalDomain;
 import cn.gov.zcy.experts.domain.renewal.ExpertsCombineRenewal;
 import cn.gov.zcy.experts.dto.AuditOperatorInfoDto;
-import cn.gov.zcy.experts.dto.expert.BelongLibraryContent;
-import cn.gov.zcy.experts.dto.expert.ExpertNotifyDTO;
-import cn.gov.zcy.experts.dto.expert.IntentionListQueryDto;
+import cn.gov.zcy.experts.dto.expert.*;
 import cn.gov.zcy.experts.enums.*;
 import cn.gov.zcy.experts.factory.ExpertServiceFactory;
 import cn.gov.zcy.experts.manage.DealExpertEmploymentDateManage;
 import cn.gov.zcy.experts.manage.ExpertNumGenerateManager;
 import cn.gov.zcy.experts.notice.MessageNotice;
-import cn.gov.zcy.experts.service.ExpertManageWriteService;
-import cn.gov.zcy.experts.service.ExpertSaveInformationService;
-import cn.gov.zcy.experts.service.ExpertSubscribeService;
-import cn.gov.zcy.experts.service.ExpertsRetiredRecordService;
+import cn.gov.zcy.experts.query.ExpertAttachmentQuery;
+import cn.gov.zcy.experts.service.*;
 import cn.gov.zcy.experts.service.renewal.ExpertRenewalService;
 import cn.gov.zcy.experts.support.thrid.neusoft.NeusoftRpc;
 import cn.gov.zcy.experts.util.DateUtils;
@@ -74,7 +71,6 @@ public class ExpertSettleWriteManage {
     private BaseDao baseDao;
     @Autowired
     private BaseFormalDao baseFormalDao;
-    private ExecutorService executorService;
     @Autowired
     private FamilyRelationFormalDao familyRelationFormalDao;
     @Autowired
@@ -159,12 +155,14 @@ public class ExpertSettleWriteManage {
     private ExpertServiceFactory expertServiceFactory;
     @Autowired
     private ExpertsTrainResultDao expertsTrainResultDao;
+    @Autowired
+    private ExpertDependedInfoComponent expertDependedInfoComponent;
+    @Autowired
+    private ThreadPoolExecutor threadPoolExecutor;
 
     @PostConstruct
     public void init() {
         ThreadFactory namedThreadFactory = new ThreadFactoryBuilder().setNameFormat("ExpertSettleWriteServiceImpl-pool-%d").build();
-        executorService = new ThreadPoolExecutor(2, 4, 2,
-                TimeUnit.SECONDS, new ArrayBlockingQueue<>(300), namedThreadFactory);
         bus = new AsyncEventBus(Executors.newFixedThreadPool(1));
         saveInformationServiceList = saveInformationServiceList.stream()
                 .sorted(Comparator.comparing(ExpertSaveInformationService::getOrder)).collect(Collectors.toList());
@@ -438,7 +436,8 @@ public class ExpertSettleWriteManage {
      * @param expertId            专家ID
      * @param belongLibraryDomain 库ID
      */
-    private void copyToFormal(BaseFormalDomain baseFormalDomain, Long expertId, BelongLibraryDomain belongLibraryDomain, Boolean isRenewal, Boolean isChangeDistrict) {
+    @Transactional
+    public void copyToFormal(BaseFormalDomain baseFormalDomain, Long expertId, BelongLibraryDomain belongLibraryDomain, Boolean isRenewal, Boolean isChangeDistrict) {
         Long libraryId = belongLibraryDomain.getId();
         // 专家库信息
         BelongLibraryFormalDomain belongLibraryFormalDomain = new BelongLibraryFormalDomain();
@@ -495,8 +494,19 @@ public class ExpertSettleWriteManage {
          */
         expertAttachmentDAO.deleteFormalDeleteByBelongId(libraryId);
         expertAttachmentDAO.formCopy(libraryId, DeleteTag.NO_DELETE.getId());
+        /**
+         *  同步被依赖库信息
+         */
+        threadPoolExecutor.execute(() -> {
+                expertDependedInfoComponent.syncDependedInfo(baseFormalDomain, belongLibraryFormalDomain);
+                expertDependedInfoComponent.syncDependenceEmployment(belongLibraryFormalDomain);
+            }
+        );
     }
 
+
+
+
     /**
      * 提交相关流程操作
      *

```

7. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/manage/DealExpertEmploymentDateManage.java`

```diff
@@ -1,5 +1,6 @@
 package cn.gov.zcy.experts.manage;
 
+import cn.gov.zcy.experts.component.ExpertDependedInfoComponent;
 import cn.gov.zcy.experts.component.RenewalLetterGenerateComponent;
 import cn.gov.zcy.experts.dao.BelongLibraryDao;
 import cn.gov.zcy.experts.dao.BelongLibraryFormalDao;
@@ -14,20 +15,23 @@ import cn.gov.zcy.experts.domain.ExpertsRenewalCombineRule;
 import cn.gov.zcy.experts.domain.renewal.*;
 import cn.gov.zcy.experts.dto.expert.ExpertShowDto;
 import cn.gov.zcy.experts.enums.*;
-import cn.gov.zcy.experts.notice.NoticeOptimizationNo;
 import cn.gov.zcy.experts.notice.UpComingNotice;
 import cn.gov.zcy.experts.util.DateUtils;
 import cn.hutool.core.date.DateUtil;
 import com.alibaba.fastjson.JSON;
-import com.google.common.collect.Lists;
 import lombok.extern.slf4j.Slf4j;
 import org.apache.commons.collections.CollectionUtils;
 import org.apache.commons.lang3.StringUtils;
+import org.springframework.beans.BeanUtils;
 import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.stereotype.Component;
 import org.springframework.transaction.annotation.Transactional;
 
-import java.util.*;
+import java.util.Date;
+import java.util.List;
+import java.util.Map;
+import java.util.Objects;
+import java.util.concurrent.ThreadPoolExecutor;
 import java.util.stream.Collectors;
 
 @Component
@@ -52,8 +56,10 @@ public class DealExpertEmploymentDateManage {
     private IntentionDao intentionDao;
     @Autowired
     private RenewalLetterGenerateComponent renewalLetterGenerateComponent;
-
-
+    @Autowired
+    private ExpertDependedInfoComponent expertDependedInfoComponent;
+    @Autowired
+    private ThreadPoolExecutor threadPoolExecutor;
 
     /**
      * 获取两年聘期
@@ -211,6 +217,7 @@ public class DealExpertEmploymentDateManage {
         BelongLibraryFormalDomain belongLibraryFormalDomain = getBelongLibraryFormalDomain(belongLibraryDomain);
         if (updateFlag) {
             log.info("doUpdateEmploymentDate.update belongLibraryDomain:{}", JSON.toJSONString(belongLibraryDomain));
+            belongLibraryDomain.setExamType(ExamType.RENEWAL.getId());
             belongLibraryDao.updateExpertEmployment(belongLibraryDomain);
             belongLibraryFormalDao.updateExpertEmployment(belongLibraryFormalDomain);
             syncExam(belongLibraryDomain, intentionDomain.getExpertRenewalId());
@@ -249,6 +256,7 @@ public class DealExpertEmploymentDateManage {
         } else {
             belongLibraryFormalDomain.setRenewalCount(belongLibraryFormalDomain.getRenewalCount() + 1);
         }
+        belongLibraryFormalDomain.setExamType(ExamType.RENEWAL.getId());
         return belongLibraryFormalDomain;
     }
 
@@ -292,6 +300,7 @@ public class DealExpertEmploymentDateManage {
         belongLibraryDomain.setLastContinuingContract(now);
         BelongLibraryFormalDomain belongLibraryFormalDomain = getBelongLibraryFormalDomain(belongLibraryDomain);
         if (updateFlag) {
+            belongLibraryDomain.setExamType(ExamType.RENEWAL.getId());
             belongLibraryDao.updateExpertEmployment(belongLibraryDomain);
             belongLibraryFormalDao.updateExpertEmployment(belongLibraryFormalDomain);
             syncExam(belongLibraryDomain, expertIntentionDomain.getExpertRenewalId());
@@ -308,9 +317,15 @@ public class DealExpertEmploymentDateManage {
     protected void syncExam(BelongLibraryDomain belongLibraryDomain, Long combineRenewalId) {
         List<BelongLibraryDomain> belongLibraryDomains = belongLibraryDao.findByExpertId(belongLibraryDomain.getExpertId());
         // 只有自己不同同步
+//        threadPoolExecutor.execute(() -> {
+//            BelongLibraryFormalDomain belongLibraryFormalDomain = new BelongLibraryFormalDomain();
+//            BeanUtils.copyProperties(belongLibraryDomain, belongLibraryFormalDomain);
+//            expertDependedInfoComponent.syncDependedEmployment(belongLibraryFormalDomain);
+//        });
         if (belongLibraryDomains.size() == 1) {
             return;
         }
+
         ExpertRenewalDomain cond = new ExpertRenewalDomain();
         cond.setCombineRenewalId(combineRenewalId);
         List<ExpertRenewalDomain> expertRenewalDomains = renewalDao.findExpertsExpertRenewalList(cond);
@@ -324,6 +339,7 @@ public class DealExpertEmploymentDateManage {
                         p.setLastContinuingContract(belongLibraryDomain.getLastContinuingContract());
                         p.setLastEmploymentBeginDate(belongLibraryDomain.getLastEmploymentBeginDate());
                         p.setLastEmploymentEndDate(belongLibraryDomain.getLastEmploymentEndDate());
+                        belongLibraryDomain.setExamType(ExamType.RENEWAL.getId());
                         belongLibraryDao.updateExpertEmployment(p);
                         BelongLibraryFormalDomain belongLibraryFormalDomain = getBelongLibraryFormalDomain(belongLibraryDomain);
                         belongLibraryFormalDao.updateExpertEmployment(belongLibraryFormalDomain);

```

8. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/query/BelongLibraryQuery.java`

```diff
@@ -37,4 +37,10 @@ public class BelongLibraryQuery extends BaseQuery{
      * belong表id集合
      */
     private List<Long> ids;
+
+    /**
+     * 解聘状态
+     * @see cn.gov.zcy.experts.enums.FiredStatusEnum
+     */
+    private Integer firedStatus;
 }

```

9. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/dubbo/ExpertIntentionRpcServiceImpl.java`

```diff
@@ -116,6 +116,7 @@ public class ExpertIntentionRpcServiceImpl implements ExpertIntentionRpcService
         //如果以前有考试记录获取聘期，和当前聘期比较，如果以前获取的聘期大于等于现在的新聘聘期，不生成新聘考试名单
         ExpertIntentionDomain oldIntention = intentionDao.getLatestExpertBylibraryCodeAndExpertId(libraryCode, belongLibraryDomain.getId());
         if (Objects.nonNull(oldIntention) && Objects.equals(TestStatusEnum.PASS.getId(), oldIntention.getTestStatus()) &&
+                Objects.equals(RenewalTimeType.ABSOLUTE.getId(), combineRenewal.getRenewalType()) &&
                 (Objects.nonNull(oldIntention.getEmploymentEndDate()) && oldIntention.getEmploymentEndDate().after(combineRenewal.getEmploymentEndDate()) ||
                         Objects.equals(oldIntention.getEmploymentEndDate(),combineRenewal.getEmploymentEndDate()))) {
             return Response.ok(intentionResultDTO);

```

10. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/information/ExpertBaseSaveInformationServiceImpl.java`

```diff
@@ -195,6 +195,7 @@ public class ExpertBaseSaveInformationServiceImpl implements ExpertSaveInformati
 
         if (existLibrary == null) {
 
+            libraryDomain.setFiredStatus(FiredStatusEnum.NORMAL.getValue());
             libraryDomain.setIsDelete(DeleteTag.NO_DELETE.getId());
             libraryDomain.setExpertLevel(ExpertLevel.NORMAL.getId());
             // 是重新入驻

```

11. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/information/ExpertOtherMateriaSaveInformationServiceImpl.java`

```diff
@@ -20,6 +20,7 @@ import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.stereotype.Service;
 
 import java.util.List;
+import java.util.Objects;
 
 /**
  * 其他信息保存
@@ -66,7 +67,7 @@ public class ExpertOtherMateriaSaveInformationServiceImpl implements ExpertSaveI
                     //control.setBusinessDomainAble(other);
                     otherMaterialDao.updateById(other);
                 } else if (other.getChangeMark() == ChangeMark.NEW.getId()) {
-                    otherMaterialDao.createIncludeId(other);
+                    otherMaterialDao.create(other);
                 } else if (other.getChangeMark() == ChangeMark.DELETE.getId()) {
                     otherMaterialDao.deleteWithId(other.getId());
                 }

```

12. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/information/ExpertTrainResultSaveInformationServiceImpl.java`

```diff
@@ -1,16 +1,23 @@
 package cn.gov.zcy.experts.service.information;
 
+import cn.gov.zcy.experts.config.CloudAndlandConfig;
+import cn.gov.zcy.experts.dao.BelongLibraryDao;
+import cn.gov.zcy.experts.dao.LibraryInfoDao;
 import cn.gov.zcy.experts.dao.renewal.ExpertsTrainResultDao;
+import cn.gov.zcy.experts.dao.renewal.RenewalDao;
 import cn.gov.zcy.experts.domain.BelongLibraryDomain;
+import cn.gov.zcy.experts.domain.LibraryInfoDomain;
 import cn.gov.zcy.experts.domain.renewal.ExpertsTrainResult;
 import cn.gov.zcy.experts.dto.SaveInformationContext;
 import cn.gov.zcy.experts.dto.expert.TrainResultDTO;
 import cn.gov.zcy.experts.dto.settle.ExpertInformationDto;
 import cn.gov.zcy.experts.dto.settle.SettleSaveFieldDto;
+import cn.gov.zcy.experts.enums.ExamType;
 import cn.gov.zcy.experts.service.ExpertSaveInformationService;
 import lombok.extern.slf4j.Slf4j;
 import org.apache.commons.collections4.CollectionUtils;
 import org.springframework.beans.BeanUtils;
+import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.stereotype.Service;
 
 import javax.annotation.Resource;
@@ -27,6 +34,13 @@ public class ExpertTrainResultSaveInformationServiceImpl implements ExpertSaveIn
     @Resource
     private ExpertsTrainResultDao trainResultDao;
 
+    @Resource
+    private CloudAndlandConfig cloudAndlandConfig;
+    @Autowired
+    private LibraryInfoDao libraryInfoDao;
+    @Autowired
+    private BelongLibraryDao belongLibraryDao;
+
 
     @Override
     public Integer getOrder() {
@@ -35,13 +49,18 @@ public class ExpertTrainResultSaveInformationServiceImpl implements ExpertSaveIn
 
     @Override
     public void saveInformation(SaveInformationContext context) {
-
         BelongLibraryDomain belongLibraryDomain
                 = context.getBelongLibraryDomain();
 
         if (Objects.isNull(belongLibraryDomain)) {
             return;
         }
+        LibraryInfoDomain libraryInfoDomain = libraryInfoDao.getLibraryInfoByCode(belongLibraryDomain.getLibraryCode());
+        if (Objects.nonNull(libraryInfoDomain) && cloudAndlandConfig.checkYunNan(libraryInfoDomain.getLibraryCode())) {
+            belongLibraryDomain.setExamType(ExamType.RENEWAL.getId());
+            belongLibraryDao.updateExpertEmployment(belongLibraryDomain);
+        }
+
 
         ExpertInformationDto expertInformationDto
                 = context.getExpertInformationDto();

```

13. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/abs/AbsExpertRenewalService.java`

```diff
@@ -1194,7 +1194,7 @@ public abstract class AbsExpertRenewalService implements ExpertRenewalService {
             return Lists.newArrayList();
         }
         List<ExpertRuleExportDTO> expertRuleExportDTOS = new ArrayList<>();
-        for (ExpertIntentionDomain expertIntentionDomain : intentionDomainList) {
+for (ExpertIntentionDomain expertIntentionDomain : intentionDomainList) {
             ExpertRuleExportDTO expertRuleExportDTO = new ExpertRuleExportDTO();
             expertRuleExportDTOS.add(expertRuleExportDTO);
             //姓名、注册号、手机号
@@ -1429,13 +1429,23 @@ public abstract class AbsExpertRenewalService implements ExpertRenewalService {
      * 推送专家到采云学院
      */
     protected void pushExpertToCaiyunXueYuan(List<ExpertIntentionDomain> intentionDomainList){
-        List<Long> operatorIds = intentionDomainList.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
-        Map<Long,String> map = baseDao.findByOperatorIds(operatorIds).stream().filter(p->StringUtils.isNotEmpty(p.getUserName())).
-                collect(Collectors.toMap(BaseDomain::getUserId,BaseDomain::getUserName,(oldValue,newValue) -> newValue));
-        intentionDomainList.forEach(item -> {
-            item.setUserName(map.get(item.getOperatorId()));
-        });
-        expertRenewalEventService.pushRuleExpert(intentionDomainList);
+        if (CollectionUtils.isEmpty(intentionDomainList)) {
+            log.warn("推送采云学院培训名单，专家列表为空");
+            return;
+        }
+        //推送采云学院培训名单
+        List<List<ExpertIntentionDomain>> elements = com.google.common.collect.Lists.partition(intentionDomainList, 1000);
+        if (CollectionUtils.isNotEmpty(elements)) {
+            for (List<ExpertIntentionDomain> partition : elements) {
+                List<Long> operatorIds = partition.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
+                Map<Long,String> map = baseDao.findByOperatorIds(operatorIds).stream().filter(p->StringUtils.isNotEmpty(p.getUserName())).
+                        collect(Collectors.toMap(BaseDomain::getUserId,BaseDomain::getUserName,(oldValue,newValue) -> newValue));
+                partition.forEach(item -> {
+                    item.setUserName(map.get(item.getOperatorId()));
+                });
+                expertRenewalEventService.pushRuleExpert(partition);
+            }
+        }
     }
 
     /**
@@ -1450,13 +1460,7 @@ public abstract class AbsExpertRenewalService implements ExpertRenewalService {
             List<ExpertIntentionDomain> intentionDomainList = buildSettleIntentionList(expertList, renewalDomain, combineRule);
             expertRuleManage.createExpertIntention(intentionDomainList, combineRule);
             //推送采云学院培训名单
-            List<Long> operatorIds = intentionDomainList.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
-            Map<Long,String> map = baseDao.findByOperatorIds(operatorIds).stream().filter(p->StringUtils.isNotEmpty(p.getUserName())).
-                    collect(Collectors.toMap(BaseDomain::getUserId,BaseDomain::getUserName,(oldValue,newValue) -> newValue));
-            intentionDomainList.forEach(item -> {
-                item.setUserName(map.get(item.getOperatorId()));
-            });
-            expertRenewalEventService.pushRuleExpert(intentionDomainList);
+            pushExpertToCaiyunXueYuan(intentionDomainList);
         }
     }
 
@@ -1546,4 +1550,4 @@ public abstract class AbsExpertRenewalService implements ExpertRenewalService {
         }
         return intentionDomainList;
     }
-}
+}
\ No newline at end of file

```

14. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/impl/DefaultExpertRenewalService.java`

```diff
@@ -97,8 +97,9 @@ public class DefaultExpertRenewalService extends AbsExpertRenewalService {
 
 
     @Override
-    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule) {
+    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule,List<Long> belongIds) {
         ExpertQO expertQO = getRenewalExpertQo(renewalDomain);
+        expertQO.setExpertIds(belongIds);
         List<ExpertShowDto> expertList = expertsRenewalReadService.getRenewalExpertList(renewalDomain, expertQO);
         if (CollectionUtils.isNotEmpty(expertList)) {
             //创建续聘名单

```

15. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/impl/GuangXiExpertRenewalService.java`

```diff
@@ -63,8 +63,9 @@ public class GuangXiExpertRenewalService extends AbsExpertRenewalService {
 
 
     @Override
-    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule) {
+    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule,List<Long> belongIds) {
         ExpertQO expertQO = getRenewalExpertQo(renewalDomain);
+        expertQO.setExpertIds(belongIds);
         List<ExpertShowDto> expertList = expertsRenewalReadService.getRenewalExpertList(renewalDomain, expertQO);
         if (CollectionUtils.isNotEmpty(expertList)) {
             //创建续聘名单

```

16. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/impl/SxExamServiceImpl.java`

```diff
@@ -100,11 +100,12 @@ public class SxExamServiceImpl extends AbsExpertRenewalService {
 
 
     @Override
-    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule){
+    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule,List<Long> belongIds){
         //创建黑名单并推送
         handleBlackIntention(renewalDomain, combineRule);
         //创建白名单
         ExpertQO expertQO = getRenewalExpertQo(renewalDomain);
+        expertQO.setExpertIds(belongIds);
         List<ExpertShowDto> expertList = expertsRenewalReadService.getRenewalExpertList(renewalDomain, expertQO);
         if (CollectionUtils.isNotEmpty(expertList)) {
             //创建续聘名单

```

17. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/impl/YunNanExpertRenewalService.java`

```diff
@@ -85,8 +85,9 @@ public class YunNanExpertRenewalService extends AbsExpertRenewalService {
 
 
     @Override
-    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule) {
+    public void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule,List<Long> belongIds) {
         ExpertQO expertQO = getRenewalExpertQo(renewalDomain);
+        expertQO.setExpertIds(belongIds);
         List<ExpertShowDto> expertList = getRenewalExpertList(renewalDomain, expertQO);
         if (CollectionUtils.isNotEmpty(expertList)) {
             //查询365天内考试成绩，直接给予聘期

```

18. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/ExpertRenewalEventServiceImpl.java`

```diff
@@ -129,57 +129,74 @@ public class ExpertRenewalEventServiceImpl implements ExpertRenewalEventService
         if (CollectionUtils.isEmpty(expertIntentionDomains)) {
             return Response.ok(Boolean.FALSE);
         }
-        EventTaskDetailInfo eventTaskDetailInfo = new EventTaskDetailInfo();
-        eventTaskDetailInfo.setEventSource(EventSourceEnum.EXPERT.getCode());
-        eventTaskDetailInfo.setEnvironment(cloudAndlandConfig.getCloudRegion());
-        eventTaskDetailInfo.setRuleId(expertIntentionDomains.get(0).getRuleId());
-
         int size = 100;
         List<List<ExpertIntentionDomain>> partition = Lists.partition(expertIntentionDomains, size);
-        // operator和zcyUserId映射
-        List<Long> operatorIdList = expertIntentionDomains.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
-        List<BaseDomain> baseDomainList = baseDao.findByOperatorIds(operatorIdList);
-        if (CollectionUtils.isEmpty(baseDomainList)){
-            return Response.ok(Boolean.FALSE);
-        }
-        baseDomainList = baseDomainList.stream().filter(p->Objects.nonNull(p.getUserId()) && Objects.nonNull(p.getUserName())).collect(Collectors.toList());
-        if (CollectionUtils.isEmpty(baseDomainList)){
-            return Response.ok(Boolean.FALSE);
-        }
-        Map<Long,String> userNameMap = baseDomainList.stream().collect(Collectors.toMap(BaseDomain::getUserId,BaseDomain::getUserName,(oldValue,newValue) -> newValue));
-        Map<Long,Integer> operatorIdAndverifyStatusMap = baseDomainList.stream().collect(Collectors.toMap(BaseDomain::getUserId,BaseDomain::getVerifyStatus,(k1, k2)->k1));
-        partition.forEach(list -> {
+
+        for (List<ExpertIntentionDomain> intentionDomainList : partition) {
+            List<Long> operatorIdList = intentionDomainList.stream()
+                .map(ExpertIntentionDomain::getOperatorId)
+                .collect(Collectors.toList());
+
+            List<BaseDomain> baseDomainList = baseDao.findByOperatorIds(operatorIdList);
+            if (CollectionUtils.isEmpty(baseDomainList)) {
+                log.warn("未找到操作员对应的用户信息，operatorIds: {}", operatorIdList);
+                continue;
+            }
+
+            baseDomainList = baseDomainList.stream()
+                .filter(p -> Objects.nonNull(p.getUserId()) && Objects.nonNull(p.getUserName()))
+                .collect(Collectors.toList());
+
+            if (CollectionUtils.isEmpty(baseDomainList)) {
+                log.warn("用户信息不完整，operatorIds: {}", operatorIdList);
+                continue;
+            }
+
+            Map<Long, String> userNameMap = baseDomainList.stream()
+                .collect(Collectors.toMap(BaseDomain::getUserId, BaseDomain::getUserName, (oldValue, newValue) -> newValue));
+
             List<EventTaskDetailInfo.EventUserInfo> eventUserInfoList = new ArrayList<>();
-            list.forEach(p->{
-                    EventTaskDetailInfo.EventUserInfo eventUserInfo = new EventTaskDetailInfo.EventUserInfo();
-                    eventUserInfo.setUserIdNo(p.getIdNumber());
-                    eventUserInfo.setUserName(StringUtils.isNotEmpty(p.getUserName())?p.getUserName():userNameMap.get(p.getOperatorId()));
-                    eventUserInfo.setZcyOperatorId(p.getOperatorId());
-                    eventUserInfoList.add(eventUserInfo);
+            intentionDomainList.forEach(p -> {
+                EventTaskDetailInfo.EventUserInfo eventUserInfo = new EventTaskDetailInfo.EventUserInfo();
+                eventUserInfo.setUserIdNo(p.getIdNumber());
+                String userName = StringUtils.isNotEmpty(p.getUserName()) ?
+                    p.getUserName() : userNameMap.getOrDefault(p.getOperatorId(), "Unknown");
+                eventUserInfo.setUserName(userName);
+                eventUserInfo.setZcyOperatorId(p.getOperatorId());
+                eventUserInfoList.add(eventUserInfo);
             });
-            eventTaskDetailInfo.setEventUserInfoList(eventUserInfoList);
-            if (CollectionUtils.isNotEmpty(eventUserInfoList)){
+
+            if (CollectionUtils.isNotEmpty(eventUserInfoList)) {
+                EventTaskDetailInfo eventTaskDetailInfo = new EventTaskDetailInfo();
+                eventTaskDetailInfo.setEventSource(EventSourceEnum.EXPERT.getCode());
+                eventTaskDetailInfo.setEnvironment(cloudAndlandConfig.getCloudRegion());
+                eventTaskDetailInfo.setRuleId(expertIntentionDomains.get(0).getRuleId());
+                eventTaskDetailInfo.setEventUserInfoList(eventUserInfoList);
                 log.info("[eventTaskDubboService.saveEventTaskDetail]，req={}", JSON.toJSONString(eventTaskDetailInfo));
+
                 try {
                     Response<Void> response = eventTaskDubboService.saveEventTaskDetail(eventTaskDetailInfo);
                     log.info("[eventTaskDubboService.saveEventTaskDetail]，res={}", JSON.toJSONString(response));
+
                     if (Objects.isNull(response) || !response.isSuccess()) {
-                        log.error("推送培训名单失败,请立即查看 param:{},response:{}", eventTaskDetailInfo,response);
-                        return;
+                        log.error("推送培训名单失败,请立即查看 param:{},response:{}", eventTaskDetailInfo, response);
+                        continue; // 继续处理其他分区
                     }
-                    if (response.isSuccess()){
-                        //更新本地推送状态
+
+                    if (response.isSuccess()) {
                         ExpertIntentionUpdateParam intentionUpdateParam = new ExpertIntentionUpdateParam();
                         intentionUpdateParam.setCreateFlag(YesNoEnum.YES.getCode());
-                        intentionUpdateParam.setIds(list.stream().map(ExpertIntentionDomain::getId).collect(Collectors.toList()));
+                        intentionUpdateParam.setIds(intentionDomainList.stream()
+                            .map(ExpertIntentionDomain::getId)
+                            .collect(Collectors.toList()));
                         intentionDao.updateExpertIntention(intentionUpdateParam);
                     }
-                }catch (Exception e){
-                    log.error("推送专家培训名单失败,请马上查看 param:{},response:{}", eventTaskDetailInfo,e);
+                } catch (Exception e) {
+                    log.error("推送专家培训名单失败,请马上查看 param:{},error:{}", eventTaskDetailInfo, e.getMessage(), e);
                 }
-
             }
-        });
+        }
+        
         return Response.ok(Boolean.TRUE);
     }
 
@@ -391,4 +408,4 @@ public class ExpertRenewalEventServiceImpl implements ExpertRenewalEventService
         intentionResultDTO.setExpertTrainResultDTOS(trainResultDTOS);
     }
 
-}
+}
\ No newline at end of file

```

19. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/ExpertRenewalReadServiceImpl.java`

```diff
@@ -421,7 +421,7 @@ public class ExpertRenewalReadServiceImpl implements ExpertRenewalReadService {
             if (cloudAndlandConfig.checkZCY() && (queryType != null &&
                     (Arrays.asList(IntentionTypeEnum.FINISH_RENEWAL.getCode(), IntentionTypeEnum.NOT_RENEWAL.getCode()).contains(queryType)))) {
                 // 如果聘期结束时间大于等于当前时间, 且状态不为已注销，则展示续聘按钮
-                expertIntentionListDto.setRenewalBtnFlag(Objects.nonNull(domain.getEmploymentEndDate()) && domain.getEmploymentEndDate().compareTo(now) >= 0
+                expertIntentionListDto.setRenewalBtnFlag(!cloudAndlandConfig.checkYunNan(instanceCode) && Objects.nonNull(domain.getEmploymentEndDate()) && domain.getEmploymentEndDate().compareTo(now) >= 0
                         && !Arrays.asList(ExpertState.CANCEL.getId(), ExpertState.RETIRED.getId()).contains(domain.getExpertStatus())
                         && !Objects.equals(domain.getFinanceIntention(), FinanceIntention.RENEWAL.getCode())
                         && domain.getTestStatus() != TestStatusEnum.PASS.getId());

```

20. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/ExpertRenewalService.java`

```diff
@@ -81,7 +81,7 @@ public interface ExpertRenewalService {
      * @param combineRule
      * @throws ExpertCommonException
      */
-    void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule);
+    void createForamlRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule,List<Long> belongIds);
 
     /**
      * 生成临时专家考试过期,重新生成新聘名单

```

21. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/renewal/ExpertRenewalWriteServiceImpl.java`

```diff
@@ -1853,7 +1853,7 @@ public class ExpertRenewalWriteServiceImpl implements ExpertRenewalWriteService,
                     for (ExpertRenewalDomain renewalDomain : renewalDomains) {
                         ExpertRenewalService expertRenewalService = expertServiceFactory.getExpertRenewalService(combineRule.getInstanceCode());
                         log.info("ExpertRenewalWriteServiceImpl.creatRenewalIntentionBack {}", expertRenewalService.getClass());
-                        expertRenewalService.createForamlRenewalIntention(renewalDomain,combineRule);
+                        expertRenewalService.createForamlRenewalIntention(renewalDomain,combineRule,expertIds);
                     }
                 }
             }
@@ -1870,7 +1870,7 @@ public class ExpertRenewalWriteServiceImpl implements ExpertRenewalWriteService,
     public void creatRenewalIntention(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule) {
         ExpertRenewalService expertRenewalService = expertServiceFactory.getExpertRenewalService(combineRule.getInstanceCode());
         log.info("ExpertRenewalWriteServiceImpl.creatRenewalIntentionBack {}", expertRenewalService.getClass());
-        expertRenewalService.createForamlRenewalIntention(renewalDomain,combineRule);
+        expertRenewalService.createForamlRenewalIntention(renewalDomain,combineRule,new ArrayList<>());
     }
 
 //    /**
@@ -2091,7 +2091,7 @@ public class ExpertRenewalWriteServiceImpl implements ExpertRenewalWriteService,
     public void creatIntentionByExpertIds(ExpertRenewalDomain renewalDomain, ExpertsRenewalCombineRule combineRule, List<Long> expertIds) {
         ExpertRenewalService expertRenewalService = expertServiceFactory.getExpertRenewalService(combineRule.getInstanceCode());
         log.info("ExpertRenewalWriteServiceImpl.creatRenewalIntentionBack {}", expertRenewalService.getClass());
-        expertRenewalService.createForamlRenewalIntention(renewalDomain, combineRule);
+        expertRenewalService.createForamlRenewalIntention(renewalDomain, combineRule, expertIds);
     }
 
     /**

```

22. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/ExpertManageReadServiceImpl.java`

```diff
@@ -2166,7 +2166,9 @@ public class ExpertManageReadServiceImpl implements ExpertManageReadService, Exp
                 List<ExpertCertificateDto> certificateDtos = Lists.newArrayList();
                 List<CertificateDomain> certificateFormalList = certificateDao.list(expertId);
                 if (!CollectionUtils.isEmpty(certificateFormalList)) {
-                    List<CertificateDomain> certificate = certificateFormalList.stream().filter(p -> CertificateType.TITLE.getId() == p.getType()).collect(Collectors.toList());
+                    List<CertificateDomain> certificate = certificateFormalList.stream().filter(p ->
+                            CertificateType.TITLE.getId() == p.getType() && StringUtils.isNotEmpty(p.getJobTitleName())).
+                            collect(Collectors.toList());
                     if (!CollectionUtils.isEmpty(certificate)) {
                         certificate.forEach(p -> {
                             certList.add(p.getJobTitleName());
@@ -2240,7 +2242,9 @@ public class ExpertManageReadServiceImpl implements ExpertManageReadService, Exp
         List<ExpertCertificateDto> certificateDtos = Lists.newArrayList();
         List<CertificateFormalDomain> certificateFormalList = certificateFormalDao.list(expertId);
         if (!CollectionUtils.isEmpty(certificateFormalList)) {
-            List<CertificateFormalDomain> certificate = certificateFormalList.stream().filter(p -> CertificateType.TITLE.getId() == p.getType()).collect(Collectors.toList());
+            List<CertificateFormalDomain> certificate = certificateFormalList.stream().filter(p ->
+                    CertificateType.TITLE.getId() == p.getType() && StringUtils.isNotEmpty(p.getJobTitleName())).
+                    collect(Collectors.toList());
             if (!CollectionUtils.isEmpty(certificate)) {
                 certificate.forEach(p -> {
                     certList.add(p.getJobTitleName());
@@ -2847,19 +2851,27 @@ public class ExpertManageReadServiceImpl implements ExpertManageReadService, Exp
     }
 
     private void extendExam(BaseLibrarysDetailDto dto, Long libraryId) {
+        boolean needRenewalConifg = Boolean.FALSE;
+        //查询专家库续聘配置
+        Response<LibraryDto> response = libraryReadService.getLibraryAndRuleByLibraryCode(dto.getDistrictId());
+        if (response.isSuccess() && Objects.nonNull(response.getResult()) && Objects.nonNull(response.getResult().getRuleDto())
+            && Objects.equals(response.getResult().getRuleDto().getNeedRenewal(),YesNoEnum.YES.getCode())) {
+            needRenewalConifg = true;
+        }
+        //查询专家续聘规则
         ExpertRenewalDomain expertRenewalDomain = renewalDao.getLastEffectRenewalByLibraryCode(dto.getDistrictId(), null);
-        if (null != expertRenewalDomain) {
+        if (Objects.nonNull(expertRenewalDomain)) {
             ExpertIntentionDomain expertIntentionDomain = intentionDao.getLatestExpertByRenewalIdAndExpertId(expertRenewalDomain.getCombineRenewalId(), libraryId);
             if (Objects.isNull(expertIntentionDomain)) {
                 expertIntentionDomain = intentionDao.getLatestExpertBylibraryCodeAndExpertId(dto.getDistrictId(), libraryId);
             }
-            if (null!=expertIntentionDomain){
+            if (Objects.nonNull(expertIntentionDomain)){
                 IntentionResultDTO intentionResultDTO = new IntentionResultDTO();
                 intentionResultDTO.setReuslt(expertIntentionDomain.getTestStatus());
                 intentionResultDTO.setRenewalId(expertIntentionDomain.getExpertRenewalId());
                 dto.setIntentionResultDTO(intentionResultDTO);
             }
-        } else {
+        } else if(!needRenewalConifg){
             //如果当前区划没有聘期，不展示专家聘期，区划变更导致可能展示别的区划的聘期，云山逻辑，岛端都是统一省管理
             if(cloudAndlandConfig.checkZCY()){
                 dto.setLastEmploymentEndDate(null);

```

23. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/ExpertSettleReadServiceImpl.java`

```diff
@@ -6,35 +6,141 @@ import cn.gov.zcy.experts.authentication.ExpertBusinessAuthenticationComponent;
 import cn.gov.zcy.experts.component.*;
 import cn.gov.zcy.experts.config.CloudAndlandConfig;
 import cn.gov.zcy.experts.config.ExpertCommonConfig;
-import cn.gov.zcy.experts.dao.*;
+import cn.gov.zcy.experts.dao.BaseDao;
+import cn.gov.zcy.experts.dao.BaseFormalDao;
+import cn.gov.zcy.experts.dao.BelongLibraryDao;
+import cn.gov.zcy.experts.dao.BelongLibraryFormalDao;
+import cn.gov.zcy.experts.dao.BidAreaDao;
+import cn.gov.zcy.experts.dao.BigLibraryDao;
+import cn.gov.zcy.experts.dao.ExpertAttachmentDAO;
+import cn.gov.zcy.experts.dao.ExpertSnapshotDao;
+import cn.gov.zcy.experts.dao.ExpertsExpertPublicityDao;
+import cn.gov.zcy.experts.dao.ExpertsRenewalCombineRuleDao;
+import cn.gov.zcy.experts.dao.ExpertsRetiredRecordDao;
+import cn.gov.zcy.experts.dao.ExpertsReviewDao;
+import cn.gov.zcy.experts.dao.LibraryInfoDao;
+import cn.gov.zcy.experts.dao.LibraryRuleDao;
+import cn.gov.zcy.experts.dao.StateChangeDao;
 import cn.gov.zcy.experts.dao.renewal.ExpertsTrainResultDao;
 import cn.gov.zcy.experts.dao.renewal.IntentionDao;
 import cn.gov.zcy.experts.dao.renewal.RenewalDao;
-import cn.gov.zcy.experts.domain.*;
+import cn.gov.zcy.experts.domain.BaseDomain;
+import cn.gov.zcy.experts.domain.BaseFormalDomain;
+import cn.gov.zcy.experts.domain.BelongLibraryDomain;
+import cn.gov.zcy.experts.domain.BelongLibraryFormalDomain;
+import cn.gov.zcy.experts.domain.BidArea;
+import cn.gov.zcy.experts.domain.BigLibraryDomain;
+import cn.gov.zcy.experts.domain.ExpertAttachmentDO;
+import cn.gov.zcy.experts.domain.ExpertSnapshotDomain;
+import cn.gov.zcy.experts.domain.ExpertsExpertPublicityDomain;
+import cn.gov.zcy.experts.domain.ExpertsRenewalCombineRule;
+import cn.gov.zcy.experts.domain.ExpertsRetiredRecord;
+import cn.gov.zcy.experts.domain.ExpertsReviewDomain;
+import cn.gov.zcy.experts.domain.LibraryInfoDomain;
+import cn.gov.zcy.experts.domain.LibraryRuleDomain;
+import cn.gov.zcy.experts.domain.StateChange;
 import cn.gov.zcy.experts.domain.renewal.ExpertIntentionDomain;
 import cn.gov.zcy.experts.domain.renewal.ExpertRenewalDomain;
 import cn.gov.zcy.experts.domain.renewal.ExpertsTrainResult;
 import cn.gov.zcy.experts.dto.ExpertBtnReqDto;
 import cn.gov.zcy.experts.dto.ExpertsBidAreaDto;
+import cn.gov.zcy.experts.dto.ExpertsLibraryRuleConfigExtFieldsDTO;
 import cn.gov.zcy.experts.dto.ExpertsTrackQueryDto;
 import cn.gov.zcy.experts.dto.common.CodeNameDto;
 import cn.gov.zcy.experts.dto.encryptDecrypt.ExpertDecryptReq;
 import cn.gov.zcy.experts.dto.encryptDecrypt.ExpertEncryptDecryptReq;
 import cn.gov.zcy.experts.dto.encryptDecrypt.ExpertEncryptDecryptRes;
-import cn.gov.zcy.experts.dto.expert.*;
+import cn.gov.zcy.experts.dto.expert.BaseLibrarysDetailDto;
+import cn.gov.zcy.experts.dto.expert.BelongLibraryContent;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigReqDTO;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigResponseDTO;
+import cn.gov.zcy.experts.dto.expert.ExpertExamQo;
+import cn.gov.zcy.experts.dto.expert.ExpertFiredDTO;
+import cn.gov.zcy.experts.dto.expert.ExpertQO;
+import cn.gov.zcy.experts.dto.expert.ExpertRenewalQO;
+import cn.gov.zcy.experts.dto.expert.ExpertShowDto;
+import cn.gov.zcy.experts.dto.expert.ExpertsExpertPublicityResDto;
+import cn.gov.zcy.experts.dto.expert.ExpertsInfomationOptimizationDto;
 import cn.gov.zcy.experts.dto.library.BigLibraryDto;
 import cn.gov.zcy.experts.dto.library.LibraryDto;
 import cn.gov.zcy.experts.dto.library.LibrarysTreeDto;
 import cn.gov.zcy.experts.dto.renewal.IntentionQueryDTO;
-import cn.gov.zcy.experts.dto.settle.*;
-import cn.gov.zcy.experts.enums.*;
+import cn.gov.zcy.experts.dto.settle.AttachmentDto;
+import cn.gov.zcy.experts.dto.settle.AuthenticationReqDto;
+import cn.gov.zcy.experts.dto.settle.BatchGetExpertInfoReq;
+import cn.gov.zcy.experts.dto.settle.BatchGetExpertInfoRes;
+import cn.gov.zcy.experts.dto.settle.CancelDto;
+import cn.gov.zcy.experts.dto.settle.CheckDoCnacelDto;
+import cn.gov.zcy.experts.dto.settle.ExpertAddBeforeCheckDto;
+import cn.gov.zcy.experts.dto.settle.ExpertAddCheckDto;
+import cn.gov.zcy.experts.dto.settle.ExpertEmploymentInfoReq;
+import cn.gov.zcy.experts.dto.settle.ExpertEmploymentInfoRes;
+import cn.gov.zcy.experts.dto.settle.ExpertJobJudgeReq;
+import cn.gov.zcy.experts.dto.settle.ExpertJobJudgeRes;
+import cn.gov.zcy.experts.dto.settle.ExpertJudgeForgeInfo;
+import cn.gov.zcy.experts.dto.settle.ExpertNotMatchProfessionListRes;
+import cn.gov.zcy.experts.dto.settle.ExpertQueryByNumResDto;
+import cn.gov.zcy.experts.dto.settle.ExpertSnapshotDetailDto;
+import cn.gov.zcy.experts.dto.settle.ExpertSnapshotDto;
+import cn.gov.zcy.experts.dto.settle.ExpertSubmitCheckDto;
+import cn.gov.zcy.experts.dto.settle.ExpertTrainExamDto;
+import cn.gov.zcy.experts.dto.settle.ExpertUploadCheckReqDto;
+import cn.gov.zcy.experts.dto.settle.ExpertUploadDto;
+import cn.gov.zcy.experts.dto.settle.IdentityCheckDto;
+import cn.gov.zcy.experts.dto.settle.JoinLibraryReqDto;
+import cn.gov.zcy.experts.dto.settle.JoinLibraryResDto;
+import cn.gov.zcy.experts.dto.settle.LibraryInfoReqDto;
+import cn.gov.zcy.experts.dto.settle.LibraryInfoResDto;
+import cn.gov.zcy.experts.dto.settle.ListCancelReqDto;
+import cn.gov.zcy.experts.dto.settle.ListCancelResDto;
+import cn.gov.zcy.experts.dto.settle.SettleBaseDto;
+import cn.gov.zcy.experts.dto.settle.SettleCommonDetailResDto;
+import cn.gov.zcy.experts.dto.settle.SettleDetailBatchReqDto;
+import cn.gov.zcy.experts.dto.settle.SettleDetailBatchResDto;
+import cn.gov.zcy.experts.dto.settle.SettleDetailReqDto;
+import cn.gov.zcy.experts.dto.settle.SettleDetailResDto;
+import cn.gov.zcy.experts.dto.settle.SettleLibraryDto;
+import cn.gov.zcy.experts.dto.settle.SettleLibraryInfoResDto;
+import cn.gov.zcy.experts.dto.settle.SettleLibraryManageDto;
+import cn.gov.zcy.experts.dto.settle.SettleReducedDetailDto;
+import cn.gov.zcy.experts.dto.settle.VerificationCancelReqDto;
+import cn.gov.zcy.experts.dto.settle.VerificationCancelResDto;
+import cn.gov.zcy.experts.enums.DeleteTag;
+import cn.gov.zcy.experts.enums.ErrorEnum;
+import cn.gov.zcy.experts.enums.ExamType;
+import cn.gov.zcy.experts.enums.ExpertAttactmentBizTypeEnum;
+import cn.gov.zcy.experts.enums.ExpertDeployRegionEnum;
+import cn.gov.zcy.experts.enums.ExpertError;
+import cn.gov.zcy.experts.enums.ExpertIntention;
+import cn.gov.zcy.experts.enums.ExpertLibraryRuleImportFlagEnum;
+import cn.gov.zcy.experts.enums.ExpertRuleStatus;
+import cn.gov.zcy.experts.enums.ExpertState;
+import cn.gov.zcy.experts.enums.ExpertStateStatusEnum;
+import cn.gov.zcy.experts.enums.ExpertStateSubChangeTypeEnum;
+import cn.gov.zcy.experts.enums.ExpertStateSupStatusEnum;
+import cn.gov.zcy.experts.enums.ExpertVerifyStatus;
+import cn.gov.zcy.experts.enums.FiredStatusEnum;
+import cn.gov.zcy.experts.enums.LibraryTypeEnum;
+import cn.gov.zcy.experts.enums.PublicityTypeEnum;
+import cn.gov.zcy.experts.enums.RegistryType;
+import cn.gov.zcy.experts.enums.TestStatusEnum;
+import cn.gov.zcy.experts.enums.TrainExamStatusEnums;
+import cn.gov.zcy.experts.enums.VerifyState;
+import cn.gov.zcy.experts.enums.YesNoEnum;
 import cn.gov.zcy.experts.factory.ExpertServiceFactory;
+import cn.gov.zcy.experts.query.BelongLibraryQuery;
 import cn.gov.zcy.experts.query.ExpertAttachmentQuery;
 import cn.gov.zcy.experts.query.LibraryInfoQuery;
 import cn.gov.zcy.experts.query.LibraryRuleQuery;
 import cn.gov.zcy.experts.query.StateChangeQuery;
 import cn.gov.zcy.experts.service.renewal.ExpertRenewalEventService;
-import cn.gov.zcy.experts.util.*;
+import cn.gov.zcy.experts.util.BidUtil;
+import cn.gov.zcy.experts.util.CheckUserUtil;
+import cn.gov.zcy.experts.util.DateUtils;
+import cn.gov.zcy.experts.util.ExpertSettleConvertUtil;
+import cn.gov.zcy.experts.util.ExpertsConstants;
+import cn.gov.zcy.experts.util.OptimizationBeanTools;
+import cn.gov.zcy.experts.util.StringDealUtil;
 import cn.gov.zcy.paas.user.dto.Operator;
 import cn.gov.zcy.paas.user.dto.User;
 import cn.gov.zcy.paas.user.enums.Error;
@@ -48,6 +154,7 @@ import com.alibaba.fastjson.JSONObject;
 import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
 import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
 import com.baomidou.mybatisplus.core.toolkit.Wrappers;
+import com.fasterxml.jackson.databind.ObjectMapper;
 import com.google.common.collect.Lists;
 import com.google.common.collect.Maps;
 import com.google.common.collect.Sets;
@@ -60,8 +167,16 @@ import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.beans.factory.annotation.Value;
 import org.springframework.stereotype.Service;
 
-import java.math.BigDecimal;
-import java.util.*;
+import java.util.ArrayList;
+import java.util.Arrays;
+import java.util.Collections;
+import java.util.Date;
+import java.util.HashMap;
+import java.util.List;
+import java.util.Map;
+import java.util.Objects;
+import java.util.Optional;
+import java.util.Set;
 import java.util.concurrent.CountDownLatch;
 import java.util.concurrent.TimeUnit;
 import java.util.stream.Collectors;
@@ -172,6 +287,8 @@ public class ExpertSettleReadServiceImpl implements ExpertSettleReadService {
 
     @Autowired
     private ExpertsRenewalCombineRuleDao expertsRenewalCombineRuleDao;
+    @Autowired
+    private ExpertDependedInfoComponent expertDependedInfoComponent;
 
     /**
      * 挂起记录按钮
@@ -264,7 +381,7 @@ public class ExpertSettleReadServiceImpl implements ExpertSettleReadService {
             }
             Response<Boolean> canJoinDistrict = expertManageReadService.checkCanJoinDistrict(expertSubmitCheckDto.getCanJoinDistrictId(),expertSubmitCheckDto.getLibraryCode());
             if (Objects.nonNull(canJoinDistrict) && !canJoinDistrict.getResult()){
-                return Response.fail(ExpertError.BUSINESS_ERROR.getCode(), "意愿评标区划不能超过"+expertCommonConfig.getExpertCanJoinDistrictMaxSize()+"个师级区划");
+                return Response.fail(ExpertError.BUSINESS_ERROR.getCode(), "意愿评标区划不能超过"+expertCommonConfig.getExpertCanJoinDistrictMaxSize()+"个市级区划");
             }
             if (expertSubmitCheckDto.getCheckLibrary()) {
                 // 库限制
@@ -1038,6 +1155,33 @@ public class ExpertSettleReadServiceImpl implements ExpertSettleReadService {
             return Response.ok(resDto);
         }
 
+    @Override
+    public Response<SettleLibraryInfoResDto> getSettleLibraryInfoFormal (Operator operator){
+        if (operator == null || !operator.getUserType().startsWith(UserTypeEnum.EVALUATION_EXPERT.getCode())) {
+            return Response.failOfMessage("不是专家身份，无法查询");
+        }
+        BaseFormalDomain baseDomain = baseFormalDao.findByUserId(operator.getId());
+        if (baseDomain == null) {
+            log.warn("cn.gov.zcy.expertExpertSettleReadServiceImpl.getSettleLibraryInfo.findByUserId.isNull operator:{}", operator);
+            return Response.ok();
+        }
+        SettleLibraryInfoResDto resDto = new SettleLibraryInfoResDto();
+        resDto.setId(baseDomain.getId());
+        resDto.setUserName(baseDomain.getUserName());
+
+        // 获取入驻库
+        List<BelongLibraryFormalDomain> belongLibraryDomains = belongLibraryFormalDao.findByExpertId(baseDomain.getId());
+        List<SettleLibraryManageDto> settleLibraryManageDtoList = Lists.newArrayList();
+        belongLibraryDomains.forEach(belongLibraryDomain -> {
+            SettleLibraryManageDto settleLibraryManageDto = new SettleLibraryManageDto();
+            BeanUtils.copyProperties(belongLibraryDomain, settleLibraryManageDto);
+            settleLibraryManageDtoList.add(settleLibraryManageDto);
+
+        });
+        resDto.setSettleLibraryList(settleLibraryManageDtoList);
+        return Response.ok(resDto);
+    }
+
         @Override
         public Response<List<ExpertQueryByNumResDto>> getExpertByExpertNums (List < String > expertNums) {
             if (CollectionUtils.isEmpty(expertNums)) {
@@ -2395,6 +2539,28 @@ public class ExpertSettleReadServiceImpl implements ExpertSettleReadService {
             return Response.ok(expertsExpertPublicityResDto);
         }
 
+    /**
+     * 查询依赖库,如果libraryCode为空，则只查询大库依赖库，如果如果libraryCode为空传了，则查询子库依赖库
+     * @param dependenceRuleConfigReqDTO,instanceCode必传,instanceCode=军采大库，libraryCode=军采子库
+     * @param dependenceRuleConfigReqDTO.baseId 如果传了，则查询该专家在依赖库中的recordId
+     * @return 返回政采库和对应的recordId
+     */
+    @Override
+    public Response<DependenceRuleConfigResponseDTO> queryDependenceRule(DependenceRuleConfigReqDTO dependenceRuleConfigReqDTO) {
+        return expertDependedInfoComponent.queryDependenceRule(dependenceRuleConfigReqDTO);
+    }
+
+
+    /**
+     * 查询被依赖库
+     * @param dependenceRuleConfigReqDTO 传政采库
+     * @return 返回军采库
+     */
+    @Override
+    public Response<DependenceRuleConfigResponseDTO> queryDependedRule(DependenceRuleConfigReqDTO dependenceRuleConfigReqDTO) {
+        return expertDependedInfoComponent.queryDependedRule(dependenceRuleConfigReqDTO);
+    }
+
     @Override
     public Response<ExpertFiredDTO> checkFird(IdentityCheckDto identityCheckDto) {
         ExpertFiredDTO expertFiredDTO = new ExpertFiredDTO();

```

24. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/ExpertSettleWriteServiceImpl.java`

```diff
@@ -1,10 +1,7 @@
 package cn.gov.zcy.experts.service;
 
 import cn.gov.zcy.common.api.Response;
-import cn.gov.zcy.experts.component.EncryptDecryptBusinessComponent;
-import cn.gov.zcy.experts.component.ExpertBelongBidComponent;
-import cn.gov.zcy.experts.component.ExpertRegistrationGeneralDealService;
-import cn.gov.zcy.experts.component.UserInteractionServiceAdaptive;
+import cn.gov.zcy.experts.component.*;
 import cn.gov.zcy.experts.config.CloudAndlandConfig;
 import cn.gov.zcy.experts.config.ExpertCommonConfig;
 import cn.gov.zcy.experts.dao.*;
@@ -215,6 +212,8 @@ public class ExpertSettleWriteServiceImpl implements ExpertSettleWriteService {
 
     @Autowired
     private WorkdayAssortedService workdayAssortedService;
+    @Autowired
+    private ExpertDependedInfoComponent expertDependedInfoComponent;
 
     @PostConstruct
     public void init() {
@@ -588,7 +587,8 @@ public class ExpertSettleWriteServiceImpl implements ExpertSettleWriteService {
             update.setLibraryCode(settleSaveLibraryDto.getLibraryCode());
             // 获取库定义名称
             update.setLibraryName(libraryDto.getLibraryName());
-            update.setStatus(1);
+            update.setStatus(ExpertState.PENDING.getId());
+            update.setFiredStatus(FiredStatusEnum.NORMAL.getValue());
             update.setIsDelete(DeleteTag.NO_DELETE.getId());
             //update.setRegistryType(RegistryType.NET_REGISTRY.getId());
             update.setExpertLevel(ExpertLevel.NORMAL.getId());
@@ -1378,6 +1378,16 @@ public class ExpertSettleWriteServiceImpl implements ExpertSettleWriteService {
          */
         expertAttachmentDAO.updateFormalDeleteByBelongId(libraryId, DeleteTag.ALREADY_DELETE.getId());
         expertAttachmentDAO.formCopy(libraryId, DeleteTag.NO_DELETE.getId());
+        /**
+         * 同步被依赖库信息
+         */
+        executorService.execute(() -> {
+                //同步被依赖库表单信息
+                expertDependedInfoComponent.syncDependedInfo(baseFormalDomain, belongLibraryFormalDomain);
+                //同步被依赖库聘期信息
+                expertDependedInfoComponent.syncDependenceEmployment(belongLibraryFormalDomain);
+            }
+        );
     }
 
     /**
@@ -1841,7 +1851,6 @@ public class ExpertSettleWriteServiceImpl implements ExpertSettleWriteService {
             belongLibraryFormalDomain.setInitCreditScore(libraryFormalDomain.getInitCreditScore());
             belongLibraryFormalDomain.setCreditLevel(libraryFormalDomain.getCreditLevel());
             belongLibraryFormalDomain.setRenewalStatus(libraryFormalDomain.getRenewalStatus());
-
         }
     }
 

```

25. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/service/LibraryBusinessReadServiceImpl.java`

```diff
@@ -2,21 +2,27 @@ package cn.gov.zcy.experts.service;
 
 import cn.gov.zcy.common.api.Response;
 import cn.gov.zcy.experts.component.DistInteractionComponent;
+import cn.gov.zcy.experts.dao.BelongLibraryFormalDao;
 import cn.gov.zcy.experts.dao.BigLibraryDao;
 import cn.gov.zcy.experts.dao.LibraryInfoDao;
 import cn.gov.zcy.experts.dao.LibraryRuleDao;
+import cn.gov.zcy.experts.domain.BelongLibraryFormalDomain;
 import cn.gov.zcy.experts.domain.BigLibraryDomain;
 import cn.gov.zcy.experts.domain.LibraryInfoDomain;
 import cn.gov.zcy.experts.domain.LibraryRuleDomain;
+import cn.gov.zcy.experts.dto.ExpertsLibraryRuleConfigExtFieldsDTO;
 import cn.gov.zcy.experts.dto.common.CodeNameDto;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigReqDTO;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigResponseDTO;
 import cn.gov.zcy.experts.dto.library.*;
-import cn.gov.zcy.experts.enums.DeleteTag;
-import cn.gov.zcy.experts.enums.YesNoEnum;
+import cn.gov.zcy.experts.enums.*;
+import cn.gov.zcy.experts.query.BelongLibraryQuery;
 import cn.gov.zcy.experts.util.ExpertsConstants;
 import cn.gov.zcy.metadata.splinter.external.enums.EnabledEnum;
 import cn.gov.zcy.paas.user.dto.Operator;
 import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
 import com.baomidou.mybatisplus.core.toolkit.Wrappers;
+import com.fasterxml.jackson.databind.ObjectMapper;
 import com.google.common.collect.Lists;
 import lombok.extern.slf4j.Slf4j;
 import org.apache.commons.collections4.CollectionUtils;
@@ -24,10 +30,7 @@ import org.apache.commons.lang3.StringUtils;
 import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.stereotype.Service;
 
-import java.util.ArrayList;
-import java.util.List;
-import java.util.Objects;
-import java.util.Optional;
+import java.util.*;
 import java.util.stream.Collectors;
 
 /**
@@ -52,6 +55,9 @@ public class LibraryBusinessReadServiceImpl implements LibraryBusinessReadServic
     private DistInteractionComponent distInteractionComponent;
     @Autowired
     private LibraryRuleDao ruleDao;
+    @Autowired
+    private BelongLibraryFormalDao belongLibraryFormalDao;
+
 
     /**
      * 查询专家库规则
@@ -163,4 +169,219 @@ public class LibraryBusinessReadServiceImpl implements LibraryBusinessReadServic
         }
         return Response.ok(bigLibraryDtos);
     }
+
+    /**
+     * 查询依赖库信息
+     * @param dependenceRuleConfigReqDTO.instanceCode 必传，传军采大库code
+     * @param dependenceRuleConfigReqDTO.libraryCode 非必传，传军采子库code
+     * @param dependenceRuleConfigReqDTO.baseId 非必传,传专家baseId,用于查询recordId
+     * @return
+     */
+    @Override
+    public Response<DependenceRuleConfigResponseDTO> getDependenceLibrary(DependenceRuleConfigReqDTO dependenceRuleConfigReqDTO) {
+        if (Objects.isNull(dependenceRuleConfigReqDTO) || StringUtils.isEmpty(dependenceRuleConfigReqDTO.getInstanceCode())) {
+            return Response.fail("参数缺失，需提供 instanceCode");
+        }
+        String instanceCode = dependenceRuleConfigReqDTO.getInstanceCode();
+        String libraryCode = dependenceRuleConfigReqDTO.getLibraryCode();
+        LibraryRuleDomain ruleDomain = null;
+
+        // 若传了libraryCode，优先查询子库规则，否则回退查大库规则
+        if (StringUtils.isNotEmpty(libraryCode)) {
+            LibraryInfoDomain lib = libraryInfoDao.getLibraryInfoByCode(libraryCode);
+            if (lib == null) {
+                log.error("专家库不存在 libraryCode:{}", libraryCode);
+                return Response.fail("专家库不存在");
+            }
+            ruleDomain = ruleDao.selectOne(Wrappers.<LibraryRuleDomain>lambdaQuery()
+                    .eq(LibraryRuleDomain::getLibraryId, lib.getId())
+                    .eq(LibraryRuleDomain::getRuleType, LibraryTypeEnum.CHILD.getCode())
+                    .eq(LibraryRuleDomain::getIsDelete, YesNoEnum.NO.getCode()));
+            if (ruleDomain == null) {
+                return Response.ok(null);
+            }
+        } else {
+            // 只传 instanceCode，查询大库规则
+            BigLibraryDomain big = bigLibraryDao.selectOne(Wrappers.<BigLibraryDomain>lambdaQuery()
+                    .eq(BigLibraryDomain::getInstanceCode, instanceCode)
+                    .eq(BigLibraryDomain::getIsDelete, YesNoEnum.NO.getCode()));
+            if (big == null) {
+                log.error("大库不存在 instanceCode:{}", instanceCode);
+                return Response.fail("大库不存在");
+            }
+            ruleDomain = ruleDao.selectOne(Wrappers.<LibraryRuleDomain>lambdaQuery()
+                    .eq(LibraryRuleDomain::getLibraryId, big.getId())
+                    .eq(LibraryRuleDomain::getRuleType, LibraryTypeEnum.BIG.getCode()).
+                    eq(LibraryRuleDomain::getIsDelete, YesNoEnum.NO.getCode()));
+        }
+
+        if (ruleDomain == null) {
+            // 无依赖规则，返回空
+            return Response.ok(null);
+        }
+        String config = ruleDomain.getConfigExtFields();
+        if (StringUtils.isEmpty(config)) {
+            // 配置信息为空，返回空
+            return Response.ok(null);
+        }
+        ExpertsLibraryRuleConfigExtFieldsDTO extDto;
+        try {
+            ObjectMapper mapper = new ObjectMapper();
+            extDto = mapper.readValue(config, ExpertsLibraryRuleConfigExtFieldsDTO.class);
+        } catch (Exception e) {
+            log.error("解析规则配置信息失败 configExtFields:{}", config, e);
+            return Response.fail("解析规则配置信息失败");
+        }
+        if (extDto == null) {
+            return Response.ok(null);
+        }
+        DependenceRuleConfigResponseDTO resp = new DependenceRuleConfigResponseDTO();
+        // 若有 dependingBigLibraryCode / dependingSubLibraryCode 则设置到响应对象
+        if (StringUtils.isNotEmpty(extDto.getDependingBigLibraryCode())) {
+            resp.setInstanceCode(extDto.getDependingBigLibraryCode());
+        }
+        if (StringUtils.isNotEmpty(extDto.getDependingSubLibraryCode())) {
+            resp.setLibraryCode(extDto.getDependingSubLibraryCode());
+        }
+        // 若传了 baseId，则根据 dependingBigLibraryCode + dependingSubLibraryCode + baseId 查询 BelongLibraryFormalDomain 的 setteProcessId 并设置 recordId
+        if (dependenceRuleConfigReqDTO.getBaseId() != null && StringUtils.isNotEmpty(resp.getInstanceCode())) {
+            try {
+                List<String> libraryCodes = new ArrayList<>();
+                if (StringUtils.isNotEmpty(extDto.getDependingSubLibraryCode())) {
+                    libraryCodes.add(extDto.getDependingSubLibraryCode());
+                } else {
+                    //指定子库，则查询该大库下所有子库
+                    List<LibraryInfoDomain> libraryInfoDomains = libraryInfoDao.selectList(Wrappers.<LibraryInfoDomain>lambdaQuery()
+                            .eq(LibraryInfoDomain::getInstanceCode, resp.getInstanceCode())
+                            .eq(LibraryInfoDomain::getIsDelete, YesNoEnum.NO.getCode()));
+                    if (CollectionUtils.isNotEmpty(libraryInfoDomains)) {
+                        libraryCodes = libraryInfoDomains.stream().map(LibraryInfoDomain::getLibraryCode).collect(Collectors.toList());
+                    } else {
+                        return Response.ok(resp);
+                    }
+                }
+                if (Objects.isNull(dependenceRuleConfigReqDTO.getBaseId())) {
+                    BelongLibraryQuery query = new BelongLibraryQuery();
+                    query.setExpertIdList(Collections.singletonList(dependenceRuleConfigReqDTO.getBaseId()));
+                    query.setStatusList(Arrays.asList(ExpertState.NORMAL.getId(),ExpertState.SUSPEND.getId()));
+                    query.setFiredStatus(FiredStatusEnum.NORMAL.getValue());
+                    query.setLibraryCodeList(libraryCodes);
+                    List<BelongLibraryFormalDomain> formal = belongLibraryFormalDao.selectByQuery(query);
+                    if (formal != null) {
+                        resp.setRecordId(formal.get(0).getSettleProcessId());
+                    }
+                }
+            } catch (Exception e) {
+                log.error("查询 BelongLibraryFormalDomain 失败 baseId:{} instanceCode:{} libraryCode:{}", dependenceRuleConfigReqDTO.getBaseId(), resp.getInstanceCode(), resp.getLibraryCode(), e);
+                // 不阻塞主流程，仅记录日志并返回已有数据
+            }
+        }
+
+        return Response.ok(resp);
+    }
+
+
+    @Override
+    public Response<DependenceRuleConfigResponseDTO> getDependencedLibrary(DependenceRuleConfigReqDTO dependenceRuleConfigReqDTO) {
+        if (Objects.isNull(dependenceRuleConfigReqDTO) || StringUtils.isEmpty(dependenceRuleConfigReqDTO.getInstanceCode())) {
+            return Response.fail("参数缺失，需提供 instanceCode");
+        }
+        String instanceCode = dependenceRuleConfigReqDTO.getInstanceCode();
+        String libraryCode = dependenceRuleConfigReqDTO.getLibraryCode();
+        LibraryRuleDomain ruleDomain = null;
+
+        // 若传了libraryCode，优先查询子库规则，否则回退查大库规则
+        if (StringUtils.isNotEmpty(libraryCode)) {
+            LibraryInfoDomain lib = libraryInfoDao.getLibraryInfoByCode(libraryCode);
+            if (lib == null) {
+                log.error("专家库不存在 libraryCode:{}", libraryCode);
+                return Response.fail("专家库不存在");
+            }
+            ruleDomain = ruleDao.selectOne(Wrappers.<LibraryRuleDomain>lambdaQuery()
+                    .eq(LibraryRuleDomain::getLibraryId, lib.getId())
+                    .eq(LibraryRuleDomain::getRuleType, LibraryTypeEnum.CHILD.getCode())
+                    .eq(LibraryRuleDomain::getIsDelete, YesNoEnum.NO.getCode()));
+            if (ruleDomain == null) {
+                return Response.ok(null);
+            }
+        } else {
+            // 只传 instanceCode，查询大库规则
+            BigLibraryDomain big = bigLibraryDao.selectOne(Wrappers.<BigLibraryDomain>lambdaQuery()
+                    .eq(BigLibraryDomain::getInstanceCode, instanceCode)
+                    .eq(BigLibraryDomain::getIsDelete, YesNoEnum.NO.getCode()));
+            if (big == null) {
+                log.error("大库不存在 instanceCode:{}", instanceCode);
+                return Response.fail("大库不存在");
+            }
+            ruleDomain = ruleDao.selectOne(Wrappers.<LibraryRuleDomain>lambdaQuery()
+                    .eq(LibraryRuleDomain::getLibraryId, big.getId())
+                    .eq(LibraryRuleDomain::getRuleType, LibraryTypeEnum.BIG.getCode()).
+                    eq(LibraryRuleDomain::getIsDelete, YesNoEnum.NO.getCode()));
+        }
+
+        if (ruleDomain == null) {
+            // 无依赖规则，返回空
+            return Response.ok(null);
+        }
+        String config = ruleDomain.getConfigExtFields();
+        if (StringUtils.isEmpty(config)) {
+            // 配置信息为空，返回空
+            return Response.ok(null);
+        }
+        ExpertsLibraryRuleConfigExtFieldsDTO extDto;
+        try {
+            ObjectMapper mapper = new ObjectMapper();
+            extDto = mapper.readValue(config, ExpertsLibraryRuleConfigExtFieldsDTO.class);
+        } catch (Exception e) {
+            log.error("解析规则配置信息失败 configExtFields:{}", config, e);
+            return Response.fail("解析规则配置信息失败");
+        }
+        if (extDto == null) {
+            return Response.ok(null);
+        }
+        DependenceRuleConfigResponseDTO resp = new DependenceRuleConfigResponseDTO();
+        // 若有 dependingBigLibraryCode / dependingSubLibraryCode 则设置到响应对象
+        if (StringUtils.isNotEmpty(extDto.getDependedBigLibraryCode())) {
+            resp.setInstanceCode(extDto.getDependedBigLibraryCode());
+        }
+        if (StringUtils.isNotEmpty(extDto.getDependedSubLibraryCode())) {
+            resp.setLibraryCode(extDto.getDependedSubLibraryCode());
+        }
+        // 若传了 baseId，则根据 dependingBigLibraryCode + dependingSubLibraryCode + baseId 查询 BelongLibraryFormalDomain 的 setteProcessId 并设置 recordId
+        if (dependenceRuleConfigReqDTO.getBaseId() != null && StringUtils.isNotEmpty(resp.getInstanceCode())) {
+            try {
+                List<String> libraryCodes = new ArrayList<>();
+                //指定子库
+                if (StringUtils.isNotEmpty(extDto.getDependedSubLibraryCode())) {
+                    libraryCodes.add(extDto.getDependedSubLibraryCode());
+                } else {
+                    //指定大库，则查询该大库下所有子库
+                    List<LibraryInfoDomain> libraryInfoDomains = libraryInfoDao.selectList(Wrappers.<LibraryInfoDomain>lambdaQuery()
+                            .eq(LibraryInfoDomain::getInstanceCode, resp.getInstanceCode())
+                            .eq(LibraryInfoDomain::getIsDelete, YesNoEnum.NO.getCode()));
+                    if (CollectionUtils.isNotEmpty(libraryInfoDomains)) {
+                        libraryCodes = libraryInfoDomains.stream().map(LibraryInfoDomain::getLibraryCode).collect(Collectors.toList());
+                    } else {
+                        return Response.ok(resp);
+                    }
+                }
+                if (Objects.nonNull(dependenceRuleConfigReqDTO.getBaseId())){
+                    BelongLibraryQuery query = new BelongLibraryQuery();
+                    query.setExpertIdList(Collections.singletonList(dependenceRuleConfigReqDTO.getBaseId()));
+                    query.setStatusList(Arrays.asList(ExpertState.NORMAL.getId(),ExpertState.SUSPEND.getId()));
+                    query.setFiredStatus(FiredStatusEnum.NORMAL.getValue());
+                    query.setLibraryCodeList(libraryCodes);
+                    List<BelongLibraryFormalDomain> formal = belongLibraryFormalDao.selectByQuery(query);
+                    if (formal != null) {
+                        resp.setRecordId(formal.get(0).getSettleProcessId());
+                    }
+                }
+
+            } catch (Exception e) {
+                log.error("查询 BelongLibraryFormalDomain 失败 baseId:{} instanceCode:{} libraryCode:{}", dependenceRuleConfigReqDTO.getBaseId(), resp.getInstanceCode(), resp.getLibraryCode(), e);
+                // 不阻塞主流程，仅记录日志并返回已有数据
+            }
+        }
+        return Response.ok(resp);
+    }
 }
\ No newline at end of file

```

26. ✏️ 修改 `experts-general/src/main/java/cn/gov/zcy/experts/support/action/RenewalStartAction.java`

```diff
@@ -317,7 +317,9 @@ public class RenewalStartAction {
         }
         //已生效培训规则
         List<ExpertsRenewalCombineRule> needPushIntentionRules = expertsRenewalCombineRuleDao.selectList(
-                new LambdaQueryWrapper<ExpertsRenewalCombineRule>().in(ExpertsRenewalCombineRule::getRuleStatus, Arrays.asList(ExpertRuleStatus.IN_AUDITING.getCode(),ExpertRuleStatus.UNFINISHED.getCode()))
+                new LambdaQueryWrapper<ExpertsRenewalCombineRule>().in(ExpertsRenewalCombineRule::getRuleStatus,
+                                Arrays.asList(ExpertRuleStatus.XXB_IN_AUDITING.getCode(),ExpertRuleStatus.ALL_IN_AUDITING,ExpertRuleStatus.IN_AUDITING.getCode(),
+                                        ExpertRuleStatus.UNFINISHED.getCode(),ExpertRuleStatus.XXB_UNFINISHED.getCode(), ExpertRuleStatus.ALL_UNFINISHED.getCode()))
                         .eq(ExpertsRenewalCombineRule::getIsDelete, 0));
         if (CollectionUtils.isNotEmpty(needPushIntentionRules)) {
             needPushIntentionRules.forEach(p -> {
@@ -328,15 +330,7 @@ public class RenewalStartAction {
                                 eq(ExpertIntentionDomain::getNeedExam,YesNoEnum.YES.getCode())
                         //.eq(ExpertIntentionDomain::getTestStatus,TestStatusEnum.NOT_REGISTER.getId())
                 );
-                if (CollectionUtils.isNotEmpty(expertIntentionDomains)) {
-                    log.info("推送培训名单失败，重新推送 param:{}", rules.stream().map(ExpertsRenewalCombineRule::getId).collect(Collectors.toList()));
-                    List<Long> operatorIds = expertIntentionDomains.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
-                    Map<Long, String> map = baseDao.findByOperatorIds(operatorIds).stream().filter(q-> StringUtils.isNotEmpty(q.getUserName())).collect(Collectors.toMap(BaseDomain::getUserId, BaseDomain::getUserName, (oldValue, newValue) -> newValue));
-                    expertIntentionDomains.forEach(item -> {
-                        item.setUserName(map.get(item.getOperatorId()));
-                    });
-                    expertRenewalEventComponent.pushRuleExpert(expertIntentionDomains);
-                }
+                pushExpertToCaiyunXueYuan(expertIntentionDomains);
                 //推送云南
                 if (cloudAndlandConfig.checkYunNan(p.getInstanceCode())){
                     //未推送、未考试的专家，重新推送
@@ -347,17 +341,11 @@ public class RenewalStartAction {
                             //.eq(ExpertIntentionDomain::getTestStatus,TestStatusEnum.NOT_REGISTER.getId())
                     );
                     if (CollectionUtils.isNotEmpty(expertIntentions)) {
-                        // 过滤出培训课时大于60的专家（同时做空检查）
+                        // 过滤出培训通过的专家
                         List<ExpertIntentionDomain> expertIntentionYunnan = expertIntentions.stream()
                                 .filter(q -> q.getClassHour() != null && Objects.equals(q.getTrainStatus(), YesNoEnum.YES.getCode()))
                                 .collect(Collectors.toList());
-                        log.info("推送云南考试名单失败，重新推送 param:{}", rules.stream().map(ExpertsRenewalCombineRule::getId).collect(Collectors.toList()));
-                        List<Long> operatorIds = expertIntentions.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
-                        Map<Long, String> map = baseDao.findByOperatorIds(operatorIds).stream().filter(q-> StringUtils.isNotEmpty(q.getUserName())).collect(Collectors.toMap(BaseDomain::getUserId, BaseDomain::getUserName, (oldValue, newValue) -> newValue));
-                        expertIntentionYunnan.forEach(item -> {
-                            item.setUserName(map.get(item.getOperatorId()));
-                        });
-                        expertRenewalEventComponent.pushToXXBRuleExpert(expertIntentions);
+                        pushExpertToCaiyunXueYuan(expertIntentionYunnan);
                     }
                 }
                 List<ExpertsBlackIntention> blackIntentions = expertsBlackIntentionDao.selectList(
@@ -401,4 +389,23 @@ public class RenewalStartAction {
         }
 
     }
+
+    /**
+     * 推送专家到采云学院
+     */
+    protected void pushExpertToCaiyunXueYuan(List<ExpertIntentionDomain> intentionDomainList){
+        //推送采云学院培训名单
+        List<List<ExpertIntentionDomain>> elements =  com.google.common.collect.Lists.partition(intentionDomainList, 1000);
+        if (org.apache.commons.collections4.CollectionUtils.isNotEmpty(elements)) {
+            for (List<ExpertIntentionDomain> partition : elements) {
+                List<Long> operatorIds = partition.stream().map(ExpertIntentionDomain::getOperatorId).collect(Collectors.toList());
+                Map<Long,String> map = baseDao.findByOperatorIds(operatorIds).stream().filter(p->StringUtils.isNotEmpty(p.getUserName())).
+                        collect(Collectors.toMap(BaseDomain::getUserId,BaseDomain::getUserName,(oldValue,newValue) -> newValue));
+                partition.forEach(item -> {
+                    item.setUserName(map.get(item.getOperatorId()));
+                });
+                expertRenewalEventService.pushRuleExpert(partition);
+            }
+        }
+    }
 }
\ No newline at end of file

```

27. ✏️ 修改 `experts-general/src/main/resources/mapper/BelongLibraryFormalMapper.xml`

```diff
@@ -174,6 +174,9 @@
                 #{item}
             </foreach>
         </if>
+        <if test="firedStatus != null ">
+            and fired_status = #{firedStatus}
+        </if>
         <if test="statusList != null and statusList.size > 0">
             and status IN
             <foreach collection="statusList" item="item" open="(" close=")" separator=",">
@@ -336,7 +339,7 @@
     <select id="findBySettleId" parameterType="cn.gov.zcy.experts.domain.BelongLibraryFormalDomain"
             resultMap="BelongLibraryFormalMapper">
         select
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         from
         <include refid="tb"/>
         where settle_process_id = #{settleProcessId} and status!=-1
@@ -344,7 +347,7 @@
 
     <select id="findByExpertId" parameterType="java.lang.Long" resultMap="BelongLibraryFormalMapper">
         select
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         from
         <include refid="tb"/>
         where expert_id = #{expertId} and status!=-1
@@ -409,7 +412,7 @@
 
     <select id="findById" parameterType="java.lang.Long" resultMap="BelongLibraryFormalMapper">
         select
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         from
         <include refid="tb"/>
         where id = #{id}
@@ -621,7 +624,7 @@
     </select>
 
     <select id="listRenewalExpertUser" resultMap="ExpertShowMap" parameterType="cn.gov.zcy.experts.dto.expert.ExpertQO">
-        select bf.id,blf.id belongLibraryId,blf.library_code,blf.library_name,bf.user_id,
+        select bf.id,blf.id belongLibraryId,blf.library_code,blf.library_name,
         bf.user_name,bf.mobile,bf.expert_type,bf.user_id, blf.settle_process_id,bf.id_number,blf.bid_id,blf.renewal_count,
         blf.last_employment_end_date,blf.last_employment_begin_date
         from experts_belong_library_formal blf inner join experts_base_formal bf on bf.id = blf.expert_id
@@ -631,7 +634,7 @@
                 and blf.exam_type = #{settleRenewal}
              </if>
             <if test="lastEmploymentEndDate!=null">
-                and (blf.last_employment_end_date &lt;=#{lastEmploymentEndDate}
+                and (blf.last_employment_end_date &lt;#{lastEmploymentEndDate}
                 <if test="includeNullEmploymentEndDate!=null and includeNullEmploymentEndDate == 1">
                     or blf.last_employment_end_date is null
                 </if>)
@@ -724,7 +727,7 @@
     <select id="selectByQuery" parameterType="cn.gov.zcy.experts.query.BelongLibraryQuery"
             resultMap="BelongLibraryFormalMapper">
         select
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         from
         <include refid="tb"/>
         <where>
@@ -737,7 +740,7 @@
 
     <select id="findBySettleIds" parameterType="java.util.List" resultMap="BelongLibraryFormalMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE settle_process_id in
@@ -749,7 +752,7 @@
 
     <select id="findByIds" parameterType="java.util.List" resultMap="BelongLibraryFormalMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE id in
@@ -761,7 +764,7 @@
 
     <select id="findBySettleIdsAndCode" parameterType="java.util.List" resultMap="BelongLibraryFormalMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE settle_process_id in
@@ -772,7 +775,7 @@
         <foreach collection="libraryCodes" item="item" index="index" open="(" close=")" separator=",">
             #{item}
         </foreach>
-        and status !=-1
+        and status !=-1 and is_delete=0
     </select>
 
     <select id="count" resultType="java.lang.Integer" parameterType="cn.gov.zcy.experts.dto.expert.ExpertQO">
@@ -888,7 +891,7 @@
     </insert>
     <select id="listBelongLibraryByExpertIds" resultMap="BelongLibraryFormalMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         where
@@ -971,59 +974,64 @@
         WHERE id = #{id}
     </update>
 
-    <!--不要改这个sql，必须关联experts_renewal_rule表-->
+    <!-- 查询需要续聘的专家id,配置聘期规则或者专家库配置需要聘期的库-->
     <select id="getNotRenewalExpertIds" resultType="long">
-        select a.id from experts_belong_library_formal a where library_code in
-        (select  district_id from experts_expert_renewal b where  (b.employment_end_date &gt;= now() or b.renewal_end_date &gt;= now()) and b.is_delete=0)
-        and (a.last_employment_end_date is null or a.last_employment_end_date &lt; now())
-        and a.renewal_status=1
-    </select>
-
-    <select id="findByUserIdAndLibraryCode" resultMap="BelongLibraryFormalMapper">
-        select * from experts_belong_library_formal a,experts_base_formal b where a.expert_id = b.id
-        and b.user_id=#{operatorId} and library_code=#{libraryCode} limit 1
-    </select>
-    <select id="listLibraryCodeByBaseId" resultType="cn.gov.zcy.experts.dto.expert.ExpertLibraryCodeDTO">
-        select user_id baseId,library_code libraryCode from experts_belong_library_formal a,experts_base_formal b
-        WHERE a.expert_id=b.id and b.user_id in
-        <foreach item="id" collection="list" open="(" separator="," close=")">
-            #{id}
-        </foreach>
-    </select>
-    <select id="listBaseIdBylibraryId" resultType="java.lang.Long">
-        select expert_id from experts_belong_library_formal a
-        WHERE id in
-        <foreach item="id" collection="list" open="(" separator="," close=")">
-            #{id}
-        </foreach>
-    </select>
-    <select id="getSettleIdBylibraryId" resultMap="BelongLibraryFormalMapper">
-        select id,settle_process_id from experts_belong_library_formal a
-        WHERE id in
-        <foreach item="id" collection="list" open="(" separator="," close=")">
-            #{id}
-        </foreach>
-    </select>
-    <select id="listSettleIdBylibraryId" resultType="java.lang.Long">
-        select settle_process_id from experts_belong_library_formal a
-        WHERE id in
-        <foreach item="id" collection="list" open="(" separator="," close=")">
-            #{id}
-        </foreach>
-    </select>
-    <select id="listAllStatusExpert" resultMap="ExpertShowMap" parameterType="cn.gov.zcy.experts.dto.expert.ExpertQO">
-        select bf.id,bl.modified_time,blf.id
-        belongLibraryId,user_name,id_number,political_status,birthday,postcode,mobile,email,sex,bank_name,bank_account,
-        permanent_residence_id,blf.library_name,blf.library_code,blf.bid_id,blf.bid_name,blf.can_join_district_name,
-        blf.status,blf.bid_desc,blf.professional_direction,blf.last_employment_begin_date,blf.last_employment_end_date,
-        blf.approval_date,blf.expert_num,blf.expert_level,li.instance_code,bl.verify_state,bl.registry_type,blf.settle_process_id
-
-        from experts_belong_library_formal blf
-        inner join experts_belong_library bl on blf.id = bl.id
-        inner join experts_base_formal bf on bf.id = blf.expert_id
-        inner join experts_library_info li on blf.library_code = li.library_code
-        <where>
-            <!-- 专家id集合 -->
+        select a.id from experts_belong_library_formal a where (library_code in
+        <!-- 专家库配置 -->
+    (select library_code from experts_library_info where is_delete=0 and id in
+    (select library_id from experts_library_rule where need_renewal=1 and is_delete=0 and rule_type=0))
+    or library_code in
+        <!-- 续聘配置 -->
+    (select  district_id from experts_expert_renewal b where  (b.employment_end_date &gt;= now() or b.renewal_end_date &gt;= now()) and b.is_delete=0))
+    and (a.last_employment_end_date is null or a.last_employment_end_date &lt; now())
+    and a.renewal_status=1
+</select>
+
+<select id="findByUserIdAndLibraryCode" resultMap="BelongLibraryFormalMapper">
+    select * from experts_belong_library_formal a,experts_base_formal b where a.expert_id = b.id
+    and b.user_id=#{operatorId} and library_code=#{libraryCode} limit 1
+</select>
+<select id="listLibraryCodeByBaseId" resultType="cn.gov.zcy.experts.dto.expert.ExpertLibraryCodeDTO">
+    select user_id baseId,library_code libraryCode from experts_belong_library_formal a,experts_base_formal b
+    WHERE a.expert_id=b.id and b.user_id in
+    <foreach item="id" collection="list" open="(" separator="," close=")">
+        #{id}
+    </foreach>
+</select>
+<select id="listBaseIdBylibraryId" resultType="java.lang.Long">
+    select expert_id from experts_belong_library_formal a
+    WHERE id in
+    <foreach item="id" collection="list" open="(" separator="," close=")">
+        #{id}
+    </foreach>
+</select>
+<select id="getSettleIdBylibraryId" resultMap="BelongLibraryFormalMapper">
+    select id,settle_process_id from experts_belong_library_formal a
+    WHERE id in
+    <foreach item="id" collection="list" open="(" separator="," close=")">
+        #{id}
+    </foreach>
+</select>
+<select id="listSettleIdBylibraryId" resultType="java.lang.Long">
+    select settle_process_id from experts_belong_library_formal a
+    WHERE id in
+    <foreach item="id" collection="list" open="(" separator="," close=")">
+        #{id}
+    </foreach>
+</select>
+<select id="listAllStatusExpert" resultMap="ExpertShowMap" parameterType="cn.gov.zcy.experts.dto.expert.ExpertQO">
+    select bf.id,bl.modified_time,blf.id
+    belongLibraryId,user_name,id_number,political_status,birthday,postcode,mobile,email,sex,bank_name,bank_account,
+    permanent_residence_id,blf.library_name,blf.library_code,blf.bid_id,blf.bid_name,blf.can_join_district_name,
+    blf.status,blf.bid_desc,blf.professional_direction,blf.last_employment_begin_date,blf.last_employment_end_date,
+    blf.approval_date,blf.expert_num,blf.expert_level,li.instance_code,bl.verify_state,bl.registry_type,blf.settle_process_id
+
+    from experts_belong_library_formal blf
+    inner join experts_belong_library bl on blf.id = bl.id
+    inner join experts_base_formal bf on bf.id = blf.expert_id
+    inner join experts_library_info li on blf.library_code = li.library_code
+    <where>
+        <!-- 专家id集合 -->
             <if test="expertIds != null and expertIds.size > 0">
                 AND bf.id in
                 <foreach collection="expertIds" item="item" index="index" open="(" separator="," close=")">

```

28. ✏️ 修改 `experts-general/src/main/resources/mapper/BelongLibraryMapper.xml`

```diff
@@ -223,7 +223,7 @@
     </insert>
 
     <delete id="delete" parameterType="java.lang.Long">
-        UPDATE FROM
+        UPDATE
         <include refid="tb"/>
         set `is_delete` = 1,
         status=-1
@@ -310,7 +310,7 @@
 
     <select id="findByExpertId" parameterType="java.lang.Long" resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE `expert_id` = #{expertId} and status!=-1
@@ -342,7 +342,7 @@
     <select id="findBySettleId" parameterType="cn.gov.zcy.experts.domain.BelongLibraryDomain"
             resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE `settle_process_id` = #{settleProcessId}
@@ -581,7 +581,7 @@
 
     <select id="findByExpertIdNoCnacel" parameterType="java.lang.Long" resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE `expert_id` = #{expertId} and status in (1,2,3)
@@ -589,7 +589,7 @@
 
     <select id="findBySettleIds" parameterType="java.util.List" resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE settle_process_id in
@@ -639,7 +639,7 @@
 
     <select id="findById" parameterType="java.lang.Long" resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         WHERE id = #{id} and is_delete=0 and status != -1
@@ -647,7 +647,7 @@
 
     <select id="listBelongLibraryByExpertIds" resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         where is_delete=0 and status != -1
@@ -659,7 +659,7 @@
 
     <select id="listBelongLibraryByIds" resultMap="BelongLibraryMapper">
         SELECT
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         FROM
         <include refid="tb"/>
         where is_delete=0 and status != -1
@@ -704,7 +704,7 @@
     <select id="selectByQuery" parameterType="cn.gov.zcy.experts.query.BelongLibraryQuery"
             resultMap="BelongLibraryMapper">
         select
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         from
         <include refid="tb"/>
         <where>
@@ -718,7 +718,7 @@
     <select id="selectOneByQuery" parameterType="cn.gov.zcy.experts.query.BelongLibraryQuery"
             resultMap="BelongLibraryMapper">
         select
-        <include refid="cols_all"/>
+        <include refid="cols_all"/>,exam_type
         from
         <include refid="tb"/>
         <where>

```

29. ✏️ 修改 `experts-general/src/main/resources/mapper/ExpertIntentionMapper.xml`

```diff
@@ -1041,31 +1041,6 @@ notExamResult=@Integer[1],-->
           and need_exam=1
         order by employment_end_date desc
     </select>
-    <select id="queryExpertRenewalLetter" resultType="java.lang.String" parameterType="java.lang.Long">
-        select letter_attach from experts_expert_intention where expert_id = #{expertId}
-                    and (is_delete = 0 or is_delete is null) and test_status = 1 and exam_type in (1,2) and letter_attach is not null
-    </select>
-    <select id="selectNeedGenerate" resultMap="ExpertsIntentionDomainMap">
-        select * from experts_expert_intention
-        where (is_delete = 0 or is_delete is null) and test_status = 1
-            and exam_type in (1,2) and letter_attach is null and employment_end_date &gt;= '2025-01-01 00:00:00'
-          and employment_begin_date &lt;= now()
-        <if test="ruleId != null">
-            and rule_id = #{ruleId}
-        </if>
-        <if test="id != null">
-            and id = #{id}
-        </if>
-        <if test="expertId != null">
-            and expert_id = #{expertId}
-        </if>
-        <if test="libraryCodePre != null">
-            and library_code like CONCAT(#{libraryCodePre}, '%')
-        </if>
-        <if test="expertIntention != null">
-            and expert_intention = #{expertIntention}
-        </if>
-    </select>
 
     <update id="deleteByRuleId">
         update experts_expert_intention set is_delete = 1 where rule_id = #{ruleId}

```

30. ✏️ 修改 `experts-general/src/main/resources/mapper/ExpertsLibraryMapper.xml`

```diff
@@ -115,7 +115,7 @@
             </foreach>
         </if>
         <if test="libraryCodeList != null and libraryCodeList.size > 0">
-            and library_code IN
+            and belong_district_code IN
             <foreach collection="libraryCodeList" item="item" open="(" close=")" separator=",">
                 #{item}
             </foreach>

```

31. ✏️ 修改 `experts-general/src/main/resources/mapper/LibraryRuleMapper.xml`

```diff
@@ -28,10 +28,12 @@
         <result property="shareCanView" column="share_can_view"/>
         <result property="renewInApproval" column="renew_in_approval"/>
         <result property="renewApprovalKey" column="renew_approval_key"/>
+        <result property="needRenewal" column="need_renewal"/>
         <result property="shareInstance" column="share_instance"/>
         <result property="creditBeforeChange" column="credit_before_change"/>
         <result property="creditBeforeSettle" column="credit_before_settle"/>
         <result property="allowFired" column="allow_fired"/>
+        <result property="configExtFields" column="config_ext_fields"/>
     </resultMap>
 
     <sql id="cols_all">
@@ -66,7 +68,8 @@
         `credit_before_settle`,
         share_instance,
         `renew_approval_key`,
-        `allow_fired`
+        `allow_fired`,
+         `config_ext_fields`
     </sql>
 
     <sql id="vals">
@@ -96,7 +99,8 @@
         #{creditBeforeSettle},
         #{shareInstance},
         #{renewApprovalKey},
-        #{allowFired}
+        #{allowFired},
+        #{configExtFields}
     </sql>
 
     <sql id="tb">
@@ -177,6 +181,7 @@
             <if test="shareCanView != null">share_can_view = #{shareCanView} ,</if>
             <if test="renewInApproval != null">renew_in_approval = #{renewInApproval} ,</if>
             <if test="renewApprovalKey != null">renew_approval_key = #{renewApprovalKey} ,</if>
+            <if test="needRenewal != null">need_renewal = #{needRenewal} ,</if>
             <if test="sendHangMessage != null">send_hang_message = #{sendHangMessage} ,</if>
             <if test="shareInstance != null">share_instance = #{shareInstance} ,</if>
             <if test="creditBeforeChange != null">credit_before_change = #{creditBeforeChange} ,</if>
@@ -197,7 +202,7 @@
             <if test="ruleDomain.cancelInApproval != null">`cancel_in_approval` = #{ruleDomain.cancelInApproval} ,</if>
             <if test="ruleDomain.cancelApprovalKey != null">`cancel_approval_key` = #{ruleDomain.cancelApprovalKey} ,</if>
             <if test="ruleDomain.shareInstance != null">share_instance = #{ruleDomain.shareInstance} ,</if>
-
+            <if test="ruleDomain.needRenewal != null">need_renewal = #{ruleDomain.needRenewal} ,</if>
             <if test="ruleDomain.editInApproval != null">`edit_in_approval` = #{ruleDomain.editInApproval} ,</if>
             <if test="ruleDomain.editApprovalKey != null">`edit_approval_key` = #{ruleDomain.editApprovalKey} ,</if>
             <if test="ruleDomain.shareInApproval != null">`share_in_approval` = #{ruleDomain.shareInApproval} ,</if>
@@ -243,9 +248,7 @@
     </sql>
     <select id="selectByQueryNotLimit" parameterType="cn.gov.zcy.experts.query.LibraryRuleQuery"
             resultMap="LibraryDefineRuleMapper">
-        select
-        <include refid="cols_all"/>
-        from
+        select * from
         <include refid="tb"/>
         <where>
             <include refid="queryCondition"/>
@@ -262,4 +265,13 @@
             <include refid="queryCondition"/>
         </where>
     </select>
-</mapper>
+
+    <select id="selectBigLibraryRuel" parameterType="cn.gov.zcy.experts.query.LibraryRuleQuery"
+            resultType="java.lang.Long">
+        select a.instance_code,a.instance_name,b.config_ext_fields from experts_big_library a
+        left join experts_library_rule b on a.id = b.library_id
+        <where>
+            a.id = #{libraryId}
+        </where>
+    </select>
+</mapper>
\ No newline at end of file

```

32. ✏️ 修改 `experts-general/src/main/resources/mapper/OtherMaterialFormalMapper.xml`

```diff
@@ -100,4 +100,24 @@
         <include refid="tb"/>
         WHERE expert_id = #{expertId} and is_delete=0
     </select>
+
+    <insert id="insertList">
+        INSERT INTO
+        <include refid="tb"/>
+        (
+        <include refid="cols_all_exclude_id"/>
+        )
+        VALUES
+        <foreach collection="list" item="item" index="index" separator=",">
+            (
+            #{item.name},
+            #{item.instructions},
+            #{item.attachment},
+            now(),
+            now(),
+            #{item.expertId},
+            #{item.content}
+            )
+        </foreach>
+    </insert>
 </mapper>
\ No newline at end of file

```

33. ✏️ 修改 `experts-general/src/main/resources/mapper/OtherMaterialMapper.xml`

```diff
@@ -148,4 +148,22 @@
         update <include refid="tb"/> set is_delete=1 where expert_id=#{expertId}
     </update>
 
+    <insert id="insertList">
+        INSERT INTO
+        <include refid="tb"/>
+        (
+        <include refid="cols_all_exclude_id"/>
+        ) VALUES
+        <foreach collection="list" item="item" index="index" separator=",">
+            (
+            #{item.name},
+            #{item.instructions},
+            #{item.attachment},
+            now(),
+            now(),
+            #{item.expertId},
+            #{item.content}
+            )
+        </foreach>
+    </insert>
 </mapper>
\ No newline at end of file

```

34. ✏️ 修改 `experts-general-api/src/main/java/cn/gov/zcy/experts/domain/LibraryRuleDomain.java`

```diff
@@ -164,6 +164,17 @@ public class LibraryRuleDomain implements Serializable {
      */
     private Integer allowFired;
 
+    /**
+     * 配置信息
+     * @see cn.gov.zcy.experts.dto.ExpertsLibraryRuleConfigExtFieldsDTO
+     */
+    private String configExtFields;
+
+    /**
+     * 抽取 是否需要续聘 1-需要 0-不需要
+     */
+    private Integer needRenewal;
+
 
     public LibraryDefineRuleDto toDto() {
         LibraryDefineRuleDto cd = new LibraryDefineRuleDto();

```

35. 🟢 新增 `experts-general-api/src/main/java/cn/gov/zcy/experts/dto/expert/DependenceRuleConfigReqDTO.java`

```diff
@@ -0,0 +1,24 @@
+package cn.gov.zcy.experts.dto.expert;
+
+import lombok.Data;
+
+import java.io.Serializable;
+
+@Data
+public class DependenceRuleConfigReqDTO implements Serializable {
+
+    /**
+     * 大库code(必填)
+     */
+    private String instanceCode;
+
+    /**
+     * 子库code（非必填）
+     */
+    private String libraryCode;
+
+    /**
+     * experts_base.id（非必填）
+     */
+    private Long baseId;
+}

```

36. 🟢 新增 `experts-general-api/src/main/java/cn/gov/zcy/experts/dto/expert/DependenceRuleConfigResponseDTO.java`

```diff
@@ -0,0 +1,34 @@
+package cn.gov.zcy.experts.dto.expert;
+
+import lombok.Data;
+
+import java.io.Serializable;
+
+@Data
+public class DependenceRuleConfigResponseDTO implements Serializable {
+
+    /**
+     * 大库code
+     */
+    private String instanceCode;
+
+    /**
+     * 大库名称
+     */
+    private String instanceName;
+
+    /**
+     * 子库code
+     */
+    private String libraryCode;
+
+    /**
+     * 子库名称
+     */
+    private String libraryName;
+
+    /**
+     * 入驻记录id
+     */
+    private Long recordId;
+}

```

37. ✏️ 修改 `experts-general-api/src/main/java/cn/gov/zcy/experts/dto/library/LibraryDefineRuleDto.java`

```diff
@@ -146,6 +146,11 @@ public class LibraryDefineRuleDto implements Serializable {
      */
     private String shareInstance;
 
+    /**
+     * 抽取 是否需要续聘 1-需要 0-不需要
+     */
+    private Integer needRenewal;
+
     /**
      * 可以向我申请共享的大库
      */

```

38. ✏️ 修改 `experts-general-api/src/main/java/cn/gov/zcy/experts/dto/library/LibraryDto.java`

```diff
@@ -19,7 +19,7 @@ import java.io.Serializable;
  * @date 2021/3/16 2:34 下午
  */
 @Data
-public class    LibraryDto implements Serializable {
+public class LibraryDto implements Serializable {
 
     private static final long serialVersionUID = 4258891255793418470L;
 

```

39. ✏️ 修改 `experts-general-api/src/main/java/cn/gov/zcy/experts/dto/settle/SettleLibraryManageDto.java`

```diff
@@ -51,4 +51,9 @@ public class SettleLibraryManageDto implements Serializable {
      */
     private Integer status;
 
+    /**
+     * 是否已解聘
+     * @see cn.gov.zcy.experts.enums.FiredStatusEnum
+     */
+    private Integer firedStatus;
 }

```

40. ✏️ 修改 `experts-general-api/src/main/java/cn/gov/zcy/experts/service/ExpertSettleReadService.java`

```diff
@@ -8,9 +8,7 @@ import cn.gov.zcy.experts.dto.common.CodeNameDto;
 import cn.gov.zcy.experts.dto.encryptDecrypt.ExpertDecryptReq;
 import cn.gov.zcy.experts.dto.encryptDecrypt.ExpertEncryptDecryptReq;
 import cn.gov.zcy.experts.dto.encryptDecrypt.ExpertEncryptDecryptRes;
-import cn.gov.zcy.experts.dto.expert.ExpertFiredDTO;
-import cn.gov.zcy.experts.dto.expert.ExpertRenewalQO;
-import cn.gov.zcy.experts.dto.expert.ExpertsExpertPublicityResDto;
+import cn.gov.zcy.experts.dto.expert.*;
 import cn.gov.zcy.experts.dto.library.LibrarysTreeDto;
 import cn.gov.zcy.experts.dto.settle.*;
 import cn.gov.zcy.paas.user.dto.Operator;
@@ -208,6 +206,13 @@ public interface ExpertSettleReadService {
      */
     Response<SettleLibraryInfoResDto> getSettleLibraryInfo(Operator operator);
 
+    /**
+     * 获取专家入驻的基本信息
+     * @param operator
+     * @return
+     */
+    Response<SettleLibraryInfoResDto> getSettleLibraryInfoFormal(Operator operator);
+
     /**
      * 根据专家证号批量查询
      * @param expertNums
@@ -471,4 +476,21 @@ public interface ExpertSettleReadService {
      */
     Response<ExpertFiredDTO> checkFird(IdentityCheckDto identityCheckDto);
 
+    /**
+     * 查询依赖库
+     * 参数：XJJCZJK，返回XJJCZJK的依赖库说XJZFCJZJK
+     * @return
+     */
+    Response<DependenceRuleConfigResponseDTO> queryDependenceRule(DependenceRuleConfigReqDTO identityCheckDto);
+
+    /**
+     * 查询被依赖库
+     * 参数：XJZFCJZJK，返回XJZFCJZJK的被依赖库XJJCZJK
+     * @return
+     */
+    Response<DependenceRuleConfigResponseDTO> queryDependedRule(DependenceRuleConfigReqDTO identityCheckDto);
+
+
+
+
 }

```

41. ✏️ 修改 `experts-general-api/src/main/java/cn/gov/zcy/experts/service/LibraryBusinessReadService.java`

```diff
@@ -2,6 +2,8 @@ package cn.gov.zcy.experts.service;
 
 import cn.gov.zcy.common.api.Response;
 import cn.gov.zcy.experts.dto.common.CodeNameDto;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigReqDTO;
+import cn.gov.zcy.experts.dto.expert.DependenceRuleConfigResponseDTO;
 import cn.gov.zcy.experts.dto.library.*;
 import cn.gov.zcy.paas.user.dto.Operator;
 
@@ -71,4 +73,18 @@ public interface LibraryBusinessReadService {
      */
     Response<List<BigLibraryDto>> listBigLibraryByCodes(BigLibraryQO bigLibraryQO);
 
+
+    /**
+     * 查询依赖库信息
+     * @param bigLibraryQO
+     * @return
+     */
+    Response<DependenceRuleConfigResponseDTO> getDependenceLibrary(DependenceRuleConfigReqDTO bigLibraryQO);
+
+    /**
+     * 查询被依赖库信息
+     * @param bigLibraryQO
+     * @return
+     */
+    Response<DependenceRuleConfigResponseDTO> getDependencedLibrary(DependenceRuleConfigReqDTO bigLibraryQO);
 }

```

42. ✏️ 修改 `experts-general-api/pom.xml`

```diff
@@ -28,6 +28,12 @@
         <dependency>
             <groupId>cn.gov.zcy.paas</groupId>
             <artifactId>user-api</artifactId>
+            <exclusions>
+                <exclusion>
+                    <groupId>cn.gov.zcy.app</groupId>
+                    <artifactId>app-sum-api</artifactId>
+                </exclusion>
+            </exclusions>
         </dependency>
         <!-- 用户体系依赖 end -->
 

```

43. ✏️ 修改 `experts-web/src/main/java/cn/gov/zcy/experts/controller/expert/ExpertRenewalController.java`

```diff
@@ -1,6 +1,5 @@
 package cn.gov.zcy.experts.controller.expert;
 
-import cn.gov.zcy.common.util.StringUtil;
 import cn.gov.zcy.experts.config.CloudAndlandConfig;
 import cn.gov.zcy.experts.config.ExpertCommonConfig;
 import cn.gov.zcy.experts.dao.BaseDao;
@@ -46,13 +45,13 @@ import io.terminus.common.model.Response;
 import io.terminus.common.utils.JsonMapper;
 import lombok.Cleanup;
 import lombok.extern.slf4j.Slf4j;
+import org.apache.commons.lang3.StringUtils;
 import org.apache.poi.ss.usermodel.*;
 import org.springframework.beans.BeanUtils;
 import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.beans.factory.annotation.Value;
 import org.springframework.http.MediaType;
 import org.springframework.util.CollectionUtils;
-import org.springframework.util.StringUtils;
 import org.springframework.web.bind.annotation.*;
 import org.springframework.web.multipart.MultipartFile;
 
@@ -770,7 +769,7 @@ public class ExpertRenewalController {
             return Response.fail("当前未登录");
         }
         String libraryCode = expertIntentionDto.getLibraryCode();
-        if (StringUtil.isEmpty(expertIntentionDto.getLibraryCode())) {
+        if (StringUtils.isEmpty(expertIntentionDto.getLibraryCode())) {
             libraryCode = operator.getTenantCode();
         }
 

```

44. ✏️ 修改 `pom.xml`

```diff
@@ -32,9 +32,9 @@
         <shardingsphere.elasticjob.version>3.0.2.5-RELEASE</shardingsphere.elasticjob.version>
         <sonar.host.url>http://sonar.paas.cai-inc.com/</sonar.host.url>
         <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
-        <experts-general-api.version>4.3.6.3-SNAPSHOT</experts-general-api.version>
+        <experts-general-api.version>4.3.6.4-RELEASE</experts-general-api.version>
         <experts-extract-api.version>4.1.1.7-RELEASE</experts-extract-api.version>
-        <experts-api.version>4.1.13-SNAPSHOT</experts-api.version>
+        <experts-api.version>4.1.13-RELEASE</experts-api.version>
         <!--Spring类库依赖-->
         <spring.version>5.3.31</spring.version>
         <spring-boot.version>2.7.18</spring-boot.version>
@@ -43,14 +43,10 @@
         <spring-boot-starter-elasticjob.version>3.0.2.16-RELEASE</spring-boot-starter-elasticjob.version>
         <!--Terminus类库依赖-->
         <terminus-common.version>2.0-SNAPSHOT</terminus-common.version>
-        <pampas.version>2.8.BUILD-SNAPSHOT</pampas.version>
-        <terminus.parana-common.version>4.0-SNAPSHOT</terminus.parana-common.version>
-        <zcy-trade.version>1.2-SNAPSHOT</zcy-trade.version>
-        <zcy-item.version>1.1-SNAPSHOT</zcy-item.version>
-        <zcy-auth-api.version>2.1.0-SNAPSHOT</zcy-auth-api.version>
+        <pampas.version>2.8.RELEASE</pampas.version>
+        <zcy-auth-api.version>2.1.1-RELEASE</zcy-auth-api.version>
         <vanyar.version>1.32.0-RELEASE</vanyar.version>
         <vanyar-gpcatalog.version>1.29.2-SNAPSHOT</vanyar-gpcatalog.version>
-        <vanyar.privilege.version>3.08.1129-SNAPSHOT</vanyar.privilege.version>
         <!--Java扩展类库依赖-->
         <jsr305.version>2.0.0</jsr305.version>
         <commons-fileupload.version>1.3</commons-fileupload.version>
@@ -91,15 +87,11 @@
         <stateless4j-version>1.0</stateless4j-version>
         <!--测试类库依赖-->
         <mockito.version>1.9.5</mockito.version>
-        <hamcrest-date.version>0.9.5</hamcrest-date.version>
-        <eagleye.version>0.0.2-SNAPSHOT</eagleye.version>
-        <zcy.trace.autowire.version>1.0.0-SNAPSHOT</zcy.trace.autowire.version>
         <workflow.version>2.0.3.4-SNAPSHOT</workflow.version>
         <vanyar.project.groupId>com.dtdream.vanyar</vanyar.project.groupId>
         <zcy.backlog.version>4.1.8.1-RELEASE</zcy.backlog.version>
         <start.redis.version>4.0.3-RELEASE</start.redis.version>
         <starter.notify.version>3.0.1-RELEASE</starter.notify.version>
-        <supplier.api>1.3.0-SNAPSHOT</supplier.api>
         <!--诚信-->
         <credit.external.api.version>1.5.0.RELEASE</credit.external.api.version>
         <easypoi-base.version>4.1.0</easypoi-base.version>
@@ -114,18 +106,18 @@
 
         <district-api.version>4.1.6-RELEASE</district-api.version>
         <user-api.version>4.1.1-RELEASE</user-api.version>
-        <user-internal-api.version>3.8.2-SNAPSHOT</user-internal-api.version>
+        <user-internal-api.version>3.9.27-RELEASE</user-internal-api.version>
         <vanyar-user-api.version>4.4.3-RELEASE</vanyar-user-api.version>
         <vanyar-privilege-api.version>6.09.17-RELEASE</vanyar-privilege-api.version>
 
         <janino.version>3.1.10</janino.version>
         <vanyar-district-api.version>1.29.0-SNAPSHOT</vanyar-district-api.version>
-        <address-api.version>3.4.2-SNAPSHOT</address-api.version>
+        <address-api.version>3.4.5-RELEASE</address-api.version>
         <zcy-item-api.version>1.3.7-SNAPSHOT</zcy-item-api.version>
         <apache-dubbo.version>3.1.12.9</apache-dubbo.version>
         <spring-boot-starter-actuator.version>3.1.5-RELEASE</spring-boot-starter-actuator.version>
         <io-netty.version>4.1.111.Final</io-netty.version>
-        <qualification-api.version>4.1.0-SNAPSHOT</qualification-api.version>
+        <qualification-api.version>4.3.1-RELEASE</qualification-api.version>
         <zcy-user-crypt-api.version>1.0-SNAPSHOT</zcy-user-crypt-api.version>
         <zcy-user-crypt-client.version>1.1-SNAPSHOT</zcy-user-crypt-client.version>
         <zeye-logback-filter.version>1.0.3-RELEASE</zeye-logback-filter.version>
@@ -139,7 +131,7 @@
 
         <vanyar-time-utils.version>1.29.0-SNAPSHOT</vanyar-time-utils.version>
         <pinyin4j.version>2.5.0</pinyin4j.version>
-        <paas-common.version>3.1.4-SNAPSHOT</paas-common.version>
+        <paas-common.version>3.2.27-RELEASE</paas-common.version>
         <spring-security-crypto.version>5.7.11</spring-security-crypto.version>
         <org-hibernate-hibernate-validator.version>5.0.1.Final</org-hibernate-hibernate-validator.version>
         <tomcat-embed.version>9.0.83</tomcat-embed.version>
@@ -154,7 +146,7 @@
         <mockito-junit-jupiter.version>4.5.1</mockito-junit-jupiter.version>
         <zcy-elasticjob.version>3.5.0-RELEASE</zcy-elasticjob.version>
         <reflectasm.version>1.11.9</reflectasm.version>
-        <zcy-elearning-api.version>0.0.18-SNAPSHOT</zcy-elearning-api.version>
+        <zcy-elearning-api.version>0.0.18-RELEASE</zcy-elearning-api.version>
         <planck-college-api.version>3.0.8-SNAPSHOT</planck-college-api.version>
         <vanyar-dc-api.version>1.30.0-SNAPSHOT</vanyar-dc-api.version>
         <entity-platform-api.version>5.10.0-SNAPSHOT</entity-platform-api.version>
@@ -869,7 +861,6 @@
                     </exclusion>
                 </exclusions>
             </dependency>
-            <!-- 代办服务 end -->
             <!-- 异常处理 begin -->
             <dependency>
                 <groupId>cn.gov.zcy</groupId>
@@ -877,7 +868,7 @@
                 <version>${zcy-weberror-handle.version}</version>
             </dependency>
             <!-- 异常处理 end -->
-
+            <!-- 代办服务 end -->
             <dependency>
                 <groupId>org.springframework</groupId>
                 <artifactId>spring-core</artifactId>

```
