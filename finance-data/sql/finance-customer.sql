SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `finance-bot-service`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;


USE `finance-bot-service`;

CREATE TABLE IF NOT EXISTS `dialogue_states` (
  `sender_id` VARCHAR(255) NOT NULL COMMENT '用户唯一标识',
  `state_json` TEXT NOT NULL COMMENT '完整对话状态 JSON',
  PRIMARY KEY (`sender_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `dialogue_sessions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `sender_id` VARCHAR(255) NOT NULL COMMENT '用户唯一标识（关联 dialogue_states.sender_id）',
    `session_id` VARCHAR(255) NOT NULL COMMENT '会话ID',
    `started_at` DATETIME NOT NULL COMMENT '会话开始时间',
    `last_activity_at` DATETIME NOT NULL COMMENT '最后活动时间',
    `closed_at` DATETIME NULL COMMENT '会话关闭时间',
    `turns_json` LONGTEXT NOT NULL COMMENT '对话轮次JSON（包含所有消息）',
    `title` VARCHAR(255) DEFAULT NULL COMMENT '会话标题（概要）',
    `message_count` INT DEFAULT 0 COMMENT '消息数量',
    `last_message` TEXT DEFAULT NULL COMMENT '最后一条消息摘要',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY `uk_sender_session` (`sender_id`, `session_id`),
    INDEX `idx_sender_id` (`sender_id`),
    INDEX `idx_started_at` (`started_at`),
    INDEX `idx_last_activity` (`last_activity_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';
