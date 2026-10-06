// ============================================================
// 接口地址配置
// 后端：Spring Boot（默认 http://localhost:9533）
// 说明：H5 演示时前端由 HBuilderX dev-server 提供（端口可能是 8080/8081），
//      后端已对 localhost 任意端口放行跨域。
// 仅保留后端已实现的接口，未实现的（短信验证码/文件上传/微信登录等）已移除，
// 避免出现 404 与 undefined 地址。
// ============================================================
let apiRoot = 'http://localhost:9533/api/';

let api = {
	// 首页轮播
	banner: apiRoot + 'banner',
	// 频道
	getCategory: apiRoot + 'getCategory',
	// 新闻
	article: {
		index: apiRoot + 'getIndex',
		category: apiRoot + 'getCategory',
		detail: apiRoot + 'detail',
		// AI 摘要状态（详情页实时生成轮询，无副作用）
		aiSummary: apiRoot + 'aiSummary',
		comment: apiRoot + 'comment',
		commentDetail: apiRoot + 'commentDetail',
		commentLike: apiRoot + 'commentLike',
		addComment: apiRoot + 'addComment',
		addReply: apiRoot + 'addReply',
		like: apiRoot + 'like',
		favorite: apiRoot + 'favorite',
		favoriteList: apiRoot + 'favoriteList',
	},
	// 用户
	user: {
		login: apiRoot + 'login',
		register: apiRoot + 'register',
		index: apiRoot + 'userIndex',
		userInfo: apiRoot + 'userInfo',
		updatePassword: apiRoot + 'updatePassword',
		feedback: apiRoot + 'feedback',
		logout: apiRoot + 'logout',
	},
};

export default api;
