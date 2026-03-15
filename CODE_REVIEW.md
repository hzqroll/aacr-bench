# 代码评审报告

### 审查范围
从 `e44958bfa2` 到 `c507aea7f9` 的变更，共涉及 44 个文件，新增 1495 行，删除 278 行。

---

## 发现的问题

### 1. 严重：SQL 语法错误

**文件**: `experts-general/src/main/resources/mapper/LibraryRuleMapper.xml`
**行号**: 157

```xml
<delete id="delete" parameterType="java.lang.Long">
    UPDATE FROM
    <include refid="tb"/>
    set `is_delete` = 1
    WHERE id = #{id}
</delete>
```

**问题**: `UPDATE FROM` 是无效的 SQL 语法。标准 SQL 的 UPDATE 语句应该是 `UPDATE table_name SET...`，而不是 `UPDATE FROM table_name`。这会导致运行时 SQL 执行失败。

**建议修复**:
```xml
UPDATE
<include refid="tb"/>
set `is_delete` = 1
WHERE id = #{id}
```

---

### 2. 中等：硬编码魔法数字

**文件**: `experts-general/src/main/java/cn/gov/zcy/experts/service/ExpertSettleWriteServiceImpl.java`

**问题**: 状态值从枚举 `ExpertState.PENDING.getId()` 改为硬编码的 `1`，同时移除了 `firedStatus` 的设置。

```java
// 修改前
update.setStatus(ExpertState.PENDING.getId());
update.setFiredStatus(FiredStatusEnum.NORMAL.getValue());

// 修改后
update.setStatus(1);
```

**风险**: 硬编码数字降低了代码可读性和可维护性，如果枚举值发生变化会导致难以追踪的 bug。移除 `firedStatus` 初始化可能导致数据库字段缺少默认值。

---

### 3. 中等：移除了空值检查

**文件**: `experts-general/src/main/java/cn/gov/zcy/experts/service/ExpertManageReadServiceImpl.java`

**问题**: 证书过滤条件中移除了对 `jobTitleName` 非空的检查。

```java
// 修改前
List<CertificateDomain> certificate = certificateFormalList.stream().filter(p ->
        CertificateType.TITLE.getId() == p.getType() && StringUtils.isNotEmpty(p.getJobTitleName())).
        collect(Collectors.toList());

// 修改后
List<CertificateDomain> certificate = certificateFormalList.stream().filter(p ->
        CertificateType.TITLE.getId() == p.getType()).collect(Collectors.toList());
```

**风险**: 可能导致空值被添加到结果列表中，影响下游业务逻辑。

---

### 4. 中等：移除了 ExamType 设置

**文件**: `experts-general/src/main/java/cn/gov/zcy/experts/manage/DealExpertEmploymentDateManage.java`

**问题**: 多处移除了 `belongLibraryDomain.setExamType(ExamType.RENEWAL.getId())` 的设置。

**风险**: 更新聘期时不再设置考试类型，可能影响业务逻辑中对考试类型的判断。

---

### 5. 中等：查询逻辑变更

**文件**: `experts-general/src/main/resources/mapper/BelongLibraryFormalMapper.xml`

**问题**: `getNotRenewalExpertIds` 查询逻辑被简化，移除了对 `experts_library_rule.need_renewal=1` 的检查。

```sql
-- 修改前：检查库规则配置 OR 续聘表
WHERE (library_code IN (SELECT library_code FROM experts_library_info WHERE id IN
      (SELECT library_id FROM experts_library_rule WHERE need_renewal=1 ...))
      OR library_code IN (SELECT district_id FROM experts_expert_renewal ...))

-- 修改后：仅检查续聘表
WHERE library_code IN (SELECT district_id FROM experts_expert_renewal ...)
```

**风险**: 配置了 `need_renewal=1` 的专家库中的专家将不再被包含在续聘通知名单中，这是一个显著的业务逻辑变更。

---

### 6. 轻微：格式问题

**文件**: `experts-general-api/src/main/java/cn/gov/zcy/experts/dto/library/LibraryDto.java`
**行号**: 22

```java
// 多余的空格
public class    LibraryDto implements Serializable {
```

---

## 总结

| 严重程度 | 数量 | 关键问题 |
|---------|------|---------|
| 严重 | 1 | SQL 语法错误 `UPDATE FROM` |
| 中等 | 4 | 魔法数字、空值检查移除、ExamType 移除、查询逻辑变更 |
| 轻微 | 1 | 格式问题 |

---

## 建议

1. **必须修复**: `LibraryRuleMapper.xml` 中的 SQL 语法错误
2. **建议修复**: 恢复使用枚举常量而非硬编码数字
3. **需要确认**: 查询逻辑变更是否符合业务需求
4. **需要确认**: 移除的空值检查和 ExamType 设置是否为预期行为

---

*评审时间: 2026-03-13*
