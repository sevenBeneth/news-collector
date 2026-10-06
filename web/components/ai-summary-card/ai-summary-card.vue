<template>
	<view class="ai-summary-card" :class="{ 'is-generating': phase === 'generating', 'is-typing': phase === 'typing' }"
		v-if="summary || (live && newsId)">
		<!-- 顶部流式进度条：随打字进度增长，强调“正在生成” -->
		<view class="ai-summary-card__track" v-if="phase === 'generating' || phase === 'typing'">
			<view class="ai-summary-card__bar" :style="'width:' + progress + '%'"></view>
		</view>

		<view class="ai-summary-card__header">
			<!-- AI 徽标：生成中显示脉冲圆点 + 文案切换 -->
			<view class="ai-summary-card__badge">
				<view class="ai-summary-card__dot" v-if="isBusy"></view>
				<text>{{ isBusy ? 'AI 生成中' : 'AI 摘要' }}</text>
			</view>
			<text class="ai-summary-card__model" v-if="!isBusy && modelText">{{ modelText }}</text>
			<text class="ai-summary-card__live" v-if="!isBusy && fromLive">已实时生成</text>
		</view>

		<!-- 生成中骨架屏（还没有任何文字时展示） -->
		<view class="ai-summary-card__skeleton" v-if="phase === 'generating'">
			<view class="ai-summary-card__sk-line"></view>
			<view class="ai-summary-card__sk-line" style="width: 92%"></view>
			<view class="ai-summary-card__sk-line" style="width: 64%"></view>
		</view>

		<!-- 摘要正文：逐字输出 + 光标 -->
		<view class="ai-summary-card__body" v-else>
			<text>{{ text }}</text><text class="ai-summary-card__caret" v-if="phase === 'typing'">▍</text>
		</view>

		<!-- 关键词：打字结束后逐个渐入 -->
		<view class="ai-summary-card__kw" :class="{ 'is-in': kwReady }" v-if="kwText">
			<keyword-tags :keywords="kwText" size="small" animated />
		</view>

		<!-- 状态提示 -->
		<view class="ai-summary-card__tip">
			<text v-if="phase === 'generating'">正在调用大模型生成摘要</text>
			<text v-else-if="phase === 'typing'">AI 正在逐字输出…</text>
			<text v-else-if="phase === 'timeout'">摘要生成超时，下拉刷新可重试</text>
			<text v-else-if="phase === 'failed'">摘要生成失败，请稍后重试</text>
			<text v-else>内容由 AI 生成，仅供参考</text>
			<text class="ai-summary-card__ellipsis" v-if="phase === 'generating'">...</text>
		</view>
	</view>
</template>

<script>
import keywordTags from '@/components/keyword-tags/keyword-tags.vue';

/* 各阶段：generating 等后端生成 → typing 逐字输出 → done 完成 */
export default {
	name: 'ai-summary-card',
	components: {
		keywordTags
	},
	props: {
		// 摘要文本（为空且开启 live 时进入“实时生成”流程）
		summary: {
			type: String,
			default: ''
		},
		// 关键词，逗号分隔字符串（也兼容数组）
		keywords: {
			type: [String, Array],
			default: ''
		},
		// 生成摘要的模型名
		model: {
			type: String,
			default: ''
		},
		// 新闻ID：开启 live 时用于轮询生成状态
		newsId: {
			type: [Number, String],
			default: null
		},
		// 是否开启“实时生成”：摘要为空时轮询后端，生成好后逐字输出
		live: {
			type: Boolean,
			default: false
		},
		// 打字速度（毫秒/字）
		speed: {
			type: Number,
			default: 26
		},
		// 是否启用打字机动画
		typewriter: {
			type: Boolean,
			default: true
		}
	},
	data() {
		return {
			text: '',                 // 当前已输出的文字
			full: '',                 // 完整摘要
			phase: 'done',            // generating | typing | done | timeout | failed
			kwReady: false,           // 关键词是否渐入
			fromLive: false,          // 是否来自实时轮询
			liveModel: '',
			liveKeywords: '',         // 轮询过程中拿到的关键词
			pollTimer: null,
			typeTimer: null,
			pollCount: 0
		};
	},
	computed: {
		isBusy() {
			return this.phase === 'generating' || this.phase === 'typing';
		},
		// 关键词：优先用父组件传入的，实时生成时用轮询拿到的
		kwText() {
			return this.keywords || this.liveKeywords;
		},
		progress() {
			if (this.phase === 'generating') {
				return 12;
			}
			if (!this.full) {
				return 0;
			}
			return Math.min(100, Math.round((this.text.length / this.full.length) * 100));
		},
		modelText() {
			const m = this.liveModel || this.model;
			if (!m || m === 'demo-seed') {
				return '';
			}
			return m === 'extractive-fallback' ? '本地降级摘要' : m;
		}
	},
	watch: {
		summary: {
			immediate: true,
			handler(val) {
				if (val) {
					this.startTyping(val);
				} else if (this.live && this.newsId) {
					this.startPolling();
				}
			}
		}
	},
	beforeDestroy() {
		this.clearTimers();
	},
	// 小程序端页面卸载
	onUnload() {
		this.clearTimers();
	},
	methods: {
		clearTimers() {
			if (this.typeTimer) {
				clearTimeout(this.typeTimer);
				this.typeTimer = null;
			}
			if (this.pollTimer) {
				clearTimeout(this.pollTimer);
				this.pollTimer = null;
			}
		},

		/* ---------- 实时生成：轮询后端摘要状态 ---------- */
		startPolling() {
			this.clearTimers();
			this.phase = 'generating';
			this.kwReady = false;
			this.text = '';
			this.pollCount = 0;
			this.poll();
		},

		poll() {
			this.pollCount += 1;
			if (this.pollCount > 25) {
				this.phase = 'timeout';
				return;
			}
			this.$app.request({
				url: this.$api.article.aiSummary,
				data: { id: this.newsId },
				method: 'POST',
				dataType: 'json',
				success: res => {
					if (res.code !== 0 || !res.data) {
						this.phase = 'failed';
						return;
					}
					const d = res.data;
					if (d.ai_status === 1 && d.ai_summary) {
						this.liveModel = d.ai_model || '';
						this.fromLive = true;
						// 关键词随摘要一起返回，实时模式下用它展示
						if (d.ai_keywords) {
							this.liveKeywords = d.ai_keywords;
						}
						this.startTyping(d.ai_summary);
					} else if (d.ai_status === 2) {
						this.phase = 'failed';
					} else {
						this.pollTimer = setTimeout(() => this.poll(), 1200);
					}
				},
				fail: () => {
					this.pollTimer = setTimeout(() => this.poll(), 1500);
				}
			});
		},

		/* ---------- 打字机输出 ---------- */
		startTyping(fullText) {
			this.clearTimers();
			this.full = fullText || '';
			this.text = '';
			this.kwReady = false;
			if (!this.typewriter) {
				this.text = this.full;
				this.phase = 'done';
				this.kwReady = true;
				return;
			}
			this.phase = 'typing';
			const total = this.full.length;
			const step = total > 160 ? 3 : (total > 80 ? 2 : 1);
			let i = 0;
			// 先停顿一下，让“生成中”的动效被看到
			this.typeTimer = setTimeout(() => {
				const tick = () => {
					i += step;
					this.text = this.full.slice(0, i);
					if (i < total) {
						this.typeTimer = setTimeout(tick, this.speed);
					} else {
						this.text = this.full;
						this.phase = 'done';
						this.kwReady = true;
						this.$emit('done');
					}
				};
				tick();
			}, 260);
		}
	}
};
</script>

<style lang="scss">
@keyframes aiPulse {
	0% { transform: scale(0.7); opacity: 1; }
	70% { transform: scale(1.5); opacity: 0.25; }
	100% { transform: scale(1.5); opacity: 0; }
}

@keyframes aiShimmer {
	0% { background-position: -300rpx 0; }
	100% { background-position: 300rpx 0; }
}

@keyframes aiBlink {
	0%, 45% { opacity: 1; }
	50%, 100% { opacity: 0; }
}

@keyframes aiSlideUp {
	from { opacity: 0; transform: translateY(12rpx); }
	to { opacity: 1; transform: translateY(0); }
}

@keyframes aiGlow {
	0% { box-shadow: 0 0 0 0 rgba(198, 40, 40, 0.22); }
	70% { box-shadow: 0 0 0 12rpx rgba(198, 40, 40, 0); }
	100% { box-shadow: 0 0 0 0 rgba(198, 40, 40, 0); }
}

.ai-summary-card {
	position: relative;
	padding: 24rpx;
	border-radius: 16rpx;
	background: rgba(198, 40, 40, 0.06);
	border-left: 6rpx solid #c62828;
	overflow: hidden;

	/* 生成中：呼吸光晕 */
	&.is-generating,
	&.is-typing {
		animation: aiGlow 1.6s ease-out infinite;
	}

	/* 顶部进度条 */
	&__track {
		position: absolute;
		left: 0;
		top: 0;
		right: 0;
		height: 4rpx;
		background: rgba(198, 40, 40, 0.12);
	}

	&__bar {
		height: 4rpx;
		background: linear-gradient(90deg, #ff8a80, #c62828);
		transition: width 0.18s linear;
	}

	&__header {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	&__badge {
		display: flex;
		flex-direction: row;
		align-items: center;
		padding: 4rpx 16rpx;
		border-radius: 6rpx;
		color: #ffffff;
		background: #c62828;
		font-size: 22rpx;
		font-weight: bold;
		line-height: 1.6;
		letter-spacing: 2rpx;
	}

	/* 脉冲圆点 */
	&__dot {
		position: relative;
		width: 12rpx;
		height: 12rpx;
		margin-right: 10rpx;
		border-radius: 50%;
		background: #ffffff;

		&::after {
			content: '';
			position: absolute;
			left: -4rpx;
			top: -4rpx;
			width: 20rpx;
			height: 20rpx;
			border-radius: 50%;
			background: rgba(255, 255, 255, 0.7);
			animation: aiPulse 1.2s ease-out infinite;
		}
	}

	&__model {
		margin-left: 12rpx;
		color: #c62828;
		opacity: 0.7;
		font-size: 22rpx;
		line-height: normal;
	}

	&__live {
		margin-left: 12rpx;
		padding: 2rpx 12rpx;
		border-radius: 20rpx;
		color: #c62828;
		background: rgba(198, 40, 40, 0.12);
		font-size: 20rpx;
		line-height: 1.6;
	}

	/* 骨架屏 */
	&__skeleton {
		margin-top: 18rpx;
	}

	&__sk-line {
		height: 26rpx;
		margin-bottom: 16rpx;
		border-radius: 6rpx;
		background: linear-gradient(90deg, rgba(198, 40, 40, 0.08) 25%, rgba(198, 40, 40, 0.18) 37%, rgba(198, 40, 40, 0.08) 63%);
		background-size: 600rpx 100%;
		animation: aiShimmer 1.2s linear infinite;
	}

	&__body {
		margin-top: 16rpx;
		color: #444444;
		font-size: 28rpx;
		line-height: 1.6;
		text-align: justify;
	}

	/* 打字光标 */
	&__caret {
		margin-left: 4rpx;
		color: #c62828;
		font-size: 26rpx;
		animation: aiBlink 0.9s step-end infinite;
	}

	&__kw {
		opacity: 0;
		&.is-in {
			animation: aiSlideUp 0.36s ease-out both;
			opacity: 1;
		}
	}

	/*AI 生成提示*/
	&__tip {
		margin-top: 16rpx;
		color: #999999;
		font-size: 22rpx;
		line-height: normal;
	}

	&__ellipsis {
		animation: aiBlink 1s step-end infinite;
	}
}
</style>
