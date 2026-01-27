-- ============================================
-- Crypto Analyze 数据库表创建脚本
-- ============================================

-- 如果数据库不存在，先创建数据库
-- CREATE DATABASE IF NOT EXISTS crypto_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
-- USE crypto_db;

-- ============================================
-- 表 1: smart_wallets (聪明钱数据表)
-- ============================================

CREATE TABLE IF NOT EXISTS `smart_wallets` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `address` varchar(44) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '钱包地址 (Solana地址通常44位)',
  `chain` varchar(10) DEFAULT 'SOL' COMMENT '链类型',
  `balance` decimal(20,4) DEFAULT '0.0000' COMMENT '钱包余额(SOL)',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `is_smart_money` tinyint unsigned DEFAULT '0' COMMENT '是否聪明钱: 1=是, 0=否',
  `is_kol` tinyint unsigned DEFAULT '0' COMMENT '是否KOL: 1=是, 0=否',
  `is_whale` tinyint unsigned DEFAULT '0' COMMENT '是否巨鲸: 1=是, 0=否',
  `is_sniper` tinyint unsigned DEFAULT '0' COMMENT '是否狙击手: 1=是, 0=否',
  `twitter_handle` varchar(50) DEFAULT NULL COMMENT '推特账号(如果是KOL)',
  `uses_trojan` tinyint unsigned DEFAULT '0' COMMENT '是否使用Trojan',
  `uses_bullx` tinyint unsigned DEFAULT '0' COMMENT '是否使用BullX',
  `uses_photon` tinyint unsigned DEFAULT '0' COMMENT '是否使用Photon',
  `uses_axiom` tinyint unsigned DEFAULT '0' COMMENT '是否使用Axiom',
  `uses_bot` tinyint unsigned DEFAULT '0' COMMENT '是否使用通用Bot脚本',
  `pnl_7d` decimal(20,2) DEFAULT '0.00' COMMENT '7日盈利(USD)',
  `pnl_7d_roi` decimal(10,2) DEFAULT '0.00' COMMENT '7日收益率(%)',
  `win_rate_7d` decimal(5,2) DEFAULT '0.00' COMMENT '7日胜率(%)',
  `tx_count_7d` int DEFAULT '0' COMMENT '7日总交易次数',
  `volume_7d` decimal(20,2) DEFAULT '0.00' COMMENT '7日总交易量(USD)',
  `net_inflow_7d` decimal(20,2) DEFAULT '0.00' COMMENT '7日净流入(USD)',
  `pnl_30d` decimal(20,2) DEFAULT '0.00' COMMENT '30日盈利(USD)',
  `pnl_30d_roi` decimal(10,2) DEFAULT '0.00' COMMENT '30日收益率(%)',
  `win_rate_30d` decimal(5,2) DEFAULT '0.00' COMMENT '30日胜率(%)',
  `tx_count_30d` int DEFAULT '0' COMMENT '30日总交易次数',
  `volume_30d` decimal(20,2) DEFAULT '0.00' COMMENT '30日总交易量(USD)',
  `net_inflow_30d` decimal(20,2) DEFAULT '0.00' COMMENT '30日净流入(USD)',
  `avg_hold_time_7d` int DEFAULT '0' COMMENT '7d平均持仓时长(秒)',
  `avg_hold_time_30d` int DEFAULT NULL COMMENT '30D平均持仓时长',
  `followed_count` int DEFAULT '0' COMMENT '被追踪数',
  `remark_count` int DEFAULT '0' COMMENT '被备注数',
  PRIMARY KEY (`id`),
  KEY `idx_address` (`address`),
  KEY `idx_is_smart_money` (`is_smart_money`),
  KEY `idx_pnl_7d` (`pnl_7d`),
  KEY `idx_pnl_30d` (`pnl_30d`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='聪明钱数据表';

-- ============================================
-- 表 2: birdeye_wallet_transactions (钱包交易记录表)
-- ============================================

CREATE TABLE IF NOT EXISTS `birdeye_wallet_transactions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `tx_hash` varchar(128) COLLATE utf8mb4_general_ci NOT NULL COMMENT '交易哈希 (txHash), 唯一索引',
  `block_number` bigint DEFAULT NULL COMMENT '区块高度 (blockNumber)',
  `block_time` datetime DEFAULT NULL COMMENT '交易时间 (blockTime ISO格式转换)',
  `status` tinyint(1) DEFAULT '1' COMMENT '交易状态 (status): 1=成功, 0=失败',
  `from` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '发起交易的钱包地址 (from)',
  `to` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '交互目标地址 (to)',
  `fee` bigint DEFAULT NULL COMMENT '交易手续费 (fee), 单位: Lamports',
  `main_action` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '主要动作类型 (mainAction)',
  `balance_change` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '余额变动数组 (balanceChange)，json字符串',
  `contract_label` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '合约标签信息 (contractLabel)，json字符串',
  `token_transfers` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '代币流转明细 (tokenTransfers)，json字符串',
  `block_time_unix` bigint DEFAULT NULL COMMENT '交易时间戳，秒级',
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间',
  `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tx_hash` (`tx_hash`) COMMENT '防止重复存储同一笔交易',
  KEY `idx_from` (`from`) COMMENT '用于查询指定钱包的历史',
  KEY `idx_block_time` (`block_time`) COMMENT '用于按时间排序查询',
  KEY `idx_block_number` (`block_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Birdeye钱包历史交易记录表';

-- ============================================
-- 创建完成
-- ============================================

-- 查看表结构
-- SHOW CREATE TABLE smart_wallets;
-- SHOW CREATE TABLE birdeye_wallet_transactions;

-- 查看表列表
-- SHOW TABLES;
