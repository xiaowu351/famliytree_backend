-- 邓氏宗谱九江县城子镇初始化数据
-- 来源：新--邓氏宗谱九江县城子镇（定稿）.docx
-- 说明：
-- 1. 本 SQL 仅基于 docx 中可直接解析的 Word 表格文本生成。
-- 2. 该 docx 另含 73 张图片，图片中的谱文/人物资料未做 OCR，暂未纳入本 SQL。
-- 3. 表格呈现的是第 52 世至第 88 世的一条连续世系，本 SQL 保留原谱世次作为 generation。
-- 4. parent_id 按表格上下承接关系推断；“长子/次子/之子”等记入 rank_type。

START TRANSACTION;

DELETE FROM `members` WHERE `tree_id` = 'tree_deng_chengzizhen_001';
DELETE FROM `trees` WHERE `id` = 'tree_deng_chengzizhen_001';

INSERT INTO `trees` (
    `id`, `surname`, `title`, `hall_name`, `region`, `create_time`, `update_time`, `creator_id`
) VALUES (
    'tree_deng_chengzizhen_001',
    '邓',
    '邓氏宗谱九江县城子镇',
    '',
    '江西省九江县城子镇',
    DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'),
    DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'),
    NULL
);

INSERT INTO `members` (
    `id`, `tree_id`, `name`, `gender`, `is_alive`, `parent_id`, `spouse_id`, `desc`,
    `create_time`, `generation`, `avatar_url`, `surname`, `rank_type`, `marital_status`,
    `birth_order`, `alias_name`, `other_name`, `style_name`, `pseudonym`, `birth_date`,
    `spouse_father`, `education_school`, `education_major`, `education_degree`, `occupation`,
    `is_spouse`, `spouse_type`, `education_status`, `adoption_type`
) VALUES
('deng_czz_g52_hui', 'tree_deng_chengzizhen_001', '晦', 'M', 1, '', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 晦公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 52, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g53_tuan', 'tree_deng_chengzizhen_001', '遄', 'M', 1, 'deng_czz_g52_hui', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 遄公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 53, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g54_can', 'tree_deng_chengzizhen_001', '灿', 'M', 1, 'deng_czz_g53_tuan', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 灿公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 54, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g55_qincheng', 'tree_deng_chengzizhen_001', '勤成', 'M', 1, 'deng_czz_g54_can', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“次子 勤成”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 55, '', '邓', '次子', '', '', '监', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g56_ning', 'tree_deng_chengzizhen_001', '宁', 'M', 1, 'deng_czz_g55_qincheng', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 宁公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 56, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g57_xi', 'tree_deng_chengzizhen_001', '喜', 'M', 1, 'deng_czz_g56_ning', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“次子 喜公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 57, '', '邓', '次子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g58_ji', 'tree_deng_chengzizhen_001', '骥', 'M', 1, 'deng_czz_g57_xi', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 骥公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 58, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g59_zhi', 'tree_deng_chengzizhen_001', '志', 'M', 1, 'deng_czz_g58_ji', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 志公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 59, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g60_chun', 'tree_deng_chengzizhen_001', '纯', 'M', 1, 'deng_czz_g59_zhi', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 纯公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 60, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g61_qi', 'tree_deng_chengzizhen_001', '期', 'M', 1, 'deng_czz_g60_chun', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 期公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 61, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g62_yue', 'tree_deng_chengzizhen_001', '岳', 'M', 1, 'deng_czz_g61_qi', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 岳公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 62, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g63_jie', 'tree_deng_chengzizhen_001', '节', 'M', 1, 'deng_czz_g62_yue', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“次子 节公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 63, '', '邓', '次子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g64_lie', 'tree_deng_chengzizhen_001', '烈', 'M', 1, 'deng_czz_g63_jie', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 烈公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 64, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g65_chong', 'tree_deng_chengzizhen_001', '崇', 'M', 1, 'deng_czz_g64_lie', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 崇公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 65, '', '邓', '之子', '', '', '峰', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g66_yu', 'tree_deng_chengzizhen_001', '宇', 'M', 1, 'deng_czz_g65_chong', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 宇公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 66, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g67_huan', 'tree_deng_chengzizhen_001', '桓', 'M', 1, 'deng_czz_g66_yu', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 桓公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 67, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g68_qing', 'tree_deng_chengzizhen_001', '青', 'M', 1, 'deng_czz_g67_huan', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 青公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 68, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g69_yue', 'tree_deng_chengzizhen_001', '阅', 'M', 1, 'deng_czz_g68_qing', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“次子 阅公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 69, '', '邓', '次子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g70_ling', 'tree_deng_chengzizhen_001', '陵', 'M', 1, 'deng_czz_g69_yue', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 陵公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 70, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g71_yu', 'tree_deng_chengzizhen_001', '裕', 'M', 1, 'deng_czz_g70_ling', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 裕公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 71, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g72_can', 'tree_deng_chengzizhen_001', '参', 'M', 1, 'deng_czz_g71_yu', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 参公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 72, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g73_ben', 'tree_deng_chengzizhen_001', '本', 'M', 1, 'deng_czz_g72_can', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 本公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 73, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g74_ji', 'tree_deng_chengzizhen_001', '稽', 'M', 1, 'deng_czz_g73_ben', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 稽公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 74, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g75_li', 'tree_deng_chengzizhen_001', '离', 'M', 1, 'deng_czz_g74_ji', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 离公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 75, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g76_xu', 'tree_deng_chengzizhen_001', '旭', 'M', 1, 'deng_czz_g75_li', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 旭公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 76, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g77_kan', 'tree_deng_chengzizhen_001', '刊', 'M', 1, 'deng_czz_g76_xu', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表又注“邗”。原表记为“之子 刊公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 77, '', '邓', '之子', '', '', '邗', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g78_yi', 'tree_deng_chengzizhen_001', '毅', 'M', 1, 'deng_czz_g77_kan', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 毅公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 78, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g79_zheng', 'tree_deng_chengzizhen_001', '徵', 'M', 1, 'deng_czz_g78_yi', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 徵公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 79, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g80_qian', 'tree_deng_chengzizhen_001', '乾', 'M', 1, 'deng_czz_g79_zheng', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 乾公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 80, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g81_zheng', 'tree_deng_chengzizhen_001', '拯', 'M', 1, 'deng_czz_g80_qian', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 拯公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 81, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g82_shengqiu', 'tree_deng_chengzizhen_001', '圣求', 'M', 1, 'deng_czz_g81_zheng', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表又注“润甫”。原表记为“之子 圣求”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 82, '', '邓', '之子', '', '', '润甫', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g83_xie', 'tree_deng_chengzizhen_001', '协', 'M', 1, 'deng_czz_g82_shengqiu', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 协公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 83, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g84_jun', 'tree_deng_chengzizhen_001', '均', 'M', 1, 'deng_czz_g83_xie', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“长子 均公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 84, '', '邓', '长子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g85_shou', 'tree_deng_chengzizhen_001', '守', 'M', 1, 'deng_czz_g84_jun', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 守公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 85, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g86_zan', 'tree_deng_chengzizhen_001', '瓒', 'M', 1, 'deng_czz_g85_shou', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 瓒公”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 86, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g87_fayu', 'tree_deng_chengzizhen_001', '发玙', 'M', 1, 'deng_czz_g86_zan', '', '据《邓氏宗谱九江县城子镇》世系表录入。原表记为“之子 发玙”。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 87, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', ''),
('deng_czz_g88_dunrang', 'tree_deng_chengzizhen_001', '敦让', 'M', 1, 'deng_czz_g87_fayu', '', '据《邓氏宗谱九江县城子镇》世系表录入。表格未显示第 88 世编号，按第 87 世“发玙”下方“之子 敦让”推断为第 88 世。', DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'), 88, '', '邓', '之子', '', '', '', '', '', '', '', '', '', '', '', '', 0, '', '', '');

('deng_czz_g89_dunqing','tree_deng_chengzizhen_001','笃庆','deng_czz_g88_dunrang',89);


COMMIT;
