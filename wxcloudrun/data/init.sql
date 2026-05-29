-- 初始化数据库并生成赵氏族谱测试数据
-- 运行方式: mysql -u <username> -p < init.sql

START TRANSACTION;

DROP TABLE IF EXISTS `members`;
DROP TABLE IF EXISTS `trees`;

CREATE TABLE IF NOT EXISTS `trees` (
    `id` VARCHAR(64) PRIMARY KEY,
    `surname` VARCHAR(64) NOT NULL,
    `title` VARCHAR(128) NOT NULL,
    `hall_name` VARCHAR(128) DEFAULT NULL,
    `region` VARCHAR(255) DEFAULT NULL,
    `create_time` VARCHAR(64) NOT NULL,
    `update_time` VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `members` (
    `id` VARCHAR(64) PRIMARY KEY,
    `tree_id` VARCHAR(64) NOT NULL,
    `name` VARCHAR(64) NOT NULL,
    `gender` VARCHAR(10) NOT NULL,
    `is_alive` TINYINT(1) NOT NULL DEFAULT 1,
    `parent_id` VARCHAR(64) DEFAULT '',
    `spouse_id` VARCHAR(64) DEFAULT '',
    `desc` TEXT,
    `create_time` VARCHAR(64) NOT NULL,
    `generation` INT NOT NULL DEFAULT 1,
    `avatar_url` VARCHAR(512) DEFAULT '',
    `surname` VARCHAR(64) DEFAULT '',
    `rank_type` VARCHAR(64) DEFAULT '',
    `marital_status` VARCHAR(64) DEFAULT '',
    `birth_order` VARCHAR(64) DEFAULT '',
    `alias_name` VARCHAR(64) DEFAULT '',
    `other_name` VARCHAR(64) DEFAULT '',
    `style_name` VARCHAR(64) DEFAULT '',
    `pseudonym` VARCHAR(64) DEFAULT '',
    `birth_date` VARCHAR(64) DEFAULT '',
    `spouse_father` VARCHAR(64) DEFAULT '',
    `education_school` VARCHAR(128) DEFAULT '',
    `education_major` VARCHAR(128) DEFAULT '',
    `education_degree` VARCHAR(64) DEFAULT '',
    `occupation` VARCHAR(128) DEFAULT '',
    `is_spouse` TINYINT(1) NOT NULL DEFAULT 0,
    `spouse_type` VARCHAR(64) DEFAULT '配',
    `education_status` VARCHAR(64) DEFAULT '毕业',
    `adoption_type` VARCHAR(64) DEFAULT '生',
    `death_date` VARCHAR(64) DEFAULT '',
    `current_residence` VARCHAR(255) DEFAULT '',
    FOREIGN KEY (`tree_id`) REFERENCES `trees`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT INTO `trees` (`id`, `surname`, `title`, `hall_name`, `region`, `create_time`, `update_time`)
VALUES (
    'tree_zhao_001',
    '赵',
    '赵氏族谱',
    '天水堂',
    '浙江省杭州市',
    DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s'),
    DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s')
);

INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_01','tree_zhao_001','赵德明','M',1,'','','','2026-05-29T10:37:05',1,'','赵','始祖','','','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_01_s1','tree_zhao_001','孙氏','F',1,'','zhao_01','','2026-05-29T13:28:37',1,'','孙','配偶','','','','','','','','','','','','',1,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_02_1','tree_zhao_001','赵文远','M',1,'zhao_01','','','2026-05-29T13:18:40',2,'','赵','长子','','1','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_02_1_s1','tree_zhao_001','李氏','F',1,'','zhao_02_1','','2026-05-29T13:19:00',2,'','李','配偶','','','','','','','','','','','','',1,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_02_2','tree_zhao_001','赵文博','M',1,'zhao_01','','','2026-05-29T13:30:31',2,'','赵','次子','','2','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_02_3','tree_zhao_001','赵文婷','F',1,'zhao_01','','','2026-05-29T13:30:41',2,'','赵','长女','','3','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_02_4','tree_zhao_001','赵文杰','M',1,'zhao_01','','','2026-05-29T13:30:51',2,'','赵','三子','','4','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_03_1','tree_zhao_001','赵志强','M',1,'zhao_02_1','','','2026-05-29T13:31:00',3,'','赵','长子','','1','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_03_1_s1','tree_zhao_001','王氏','F',1,'','zhao_03_1','','2026-05-29T13:31:08',3,'','王','配偶','','','','','','','','','','','','',1,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_03_2','tree_zhao_001','赵志明','M',1,'zhao_02_1','','','2026-05-29T13:31:54',3,'','赵','次子','','2','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_03_3','tree_zhao_001','赵志勇','M',1,'zhao_02_2','','','2026-05-29T13:31:54',3,'','赵','长子','','1','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_04_1','tree_zhao_001','赵浩然','M',1,'zhao_03_1','','','2026-05-29T13:31:54',4,'','赵','长子','','1','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_04_2','tree_zhao_001','赵浩宇','M',1,'zhao_03_1','','','2026-05-29T13:31:54',4,'','赵','次子','','2','','','','','','','','','','',0,'配','毕业','生');
INSERT INTO `members` (`id`,`tree_id`,`name`,`gender`,`is_alive`,`parent_id`,`spouse_id`,`desc`,`create_time`,`generation`,`avatar_url`,`surname`,`rank_type`,`marital_status`,`birth_order`,`alias_name`,`other_name`,`style_name`,`pseudonym`,`birth_date`,`spouse_father`,`education_school`,`education_major`,`education_degree`,`occupation`,`is_spouse`,`spouse_type`,`education_status`,`adoption_type`) VALUES ('zhao_04_3','tree_zhao_001','赵雨萱','F',1,'zhao_03_1','','','2026-05-29T13:31:54',4,'','赵','长女','','3','','','','','','','','','','',0,'配','毕业','生');
COMMIT;
