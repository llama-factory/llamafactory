Llamafactory tech



最近和我的小伙伴2个人做了一个网站。

地址：https://www.llamafactory.cn LlamaFactory - AI开发者的高效工具平台



先说下基本情况，我主要擅长前端、运维，后端接口写得非常非常少。我的同伴是做自然语言处理的大佬，在这个项目中，我们分工大概是：

- `我`：开发、运维；

- `同伴`：大模块开发、产品经理、UX以及测试；



在各个阶段，我们用到的技术和工具大致如下：

### 前端：

- `Vitepress`：最开始为了快速和适配，直接选择了Vitepress做，结合配置+自定义能力做UI，但是后来UI自己设计后，有一点后悔这一选择，UI界面已经不怎么像vitepress风格了；
- `Vue3`：写主题、自定义组件等
- `TailwindCSS`：集成到Vitepress中，快速写样式，同时可以部分依赖AI生成；
- `Antdv`：使用了Ant Design中部分的组件，如弹窗、Popup、Button等，用的其实不多；
- `markdown-it`：在vitepress提供的markdown渲染之外，又自己做了部分页面的markdown自定义渲染；

### 后端：

- `NodeJS`：我有一定的Node后端的基础，但是实战不多，这次为了快，没有让同伴用Python给接口（之前项目我们用的FastAPI做后台），直接ExpressJS做了。
- `Mysql + Sequelize`：其实我们大部分数据直接用Python或者Nodejs脚本做了预处理，直接生成JSON放到前端代码中了，只是博客那一块使用mysql做存储，我们部署了rsshub定时更新指定RSS源的数据到mysql中，然后用Sequelize做ORM映射，做成接口返回给前端；

- `Github三方登录`：使用passport和passport-github集成了三方登录，这里因为cookie域的问题踩了一些坑，也是收获颇丰。
- `其他Node部分`：使用了一些helmet、margon、bcryptjs、cors等其他中间件
- `Python`：我们的数据部分，基本都要是Python提供，一部分是Rss订阅，有三个技术文档的中文化翻译，我们使用python调用大模型做的翻译，尝试过OpenAI等多家的接口。还有部分数据是用Python脚本处理的

### 运维：

- `Linux服务器`：阿里云的服务器，用了两台机器，我们是一台部署前端，一台部署后端，我们因为还有其他的网站，所以分开了；
- `域名`：一级域名我们买的都是大的技术概念的域名，想获取一些自然流量。二级域名根据功能开了不少，用的nginx的vhost部署，也方便。

- `Nignx`：静态统一管理，代理转发；
- `PM2`：管理后端NodeJS服务，监控应用；
- `SSL`：使用Certbot手动签发的SSL证书，还不想买付费的证书，以前用阿里云的免费证书，每次一年，现在三个月就到期了，就干脆放弃阿里云了改用Certbot自己签发。

### DevOps：

- `Github`： 代码托管在Github上，无需赘述。
- `GitHub Actions`：使用Github Actions监听代码的推送，代码push到github自动触发流水线，自动打包，并将打包产物发布到阿里云服务器上，基本可以做到，push三分钟后刷新网页就可以看到修改点。

### AI工具：

- `Cursor`: 我和同伴两人能力和精力有限，主要业余在做这个网站，所以我们很依赖AI来提高效率，我们这个网站的后端主要依靠它生成代码，前端代码它也是极大功劳；Cursor真的太好用了，建议所有程序员都赶紧换上。
- `Claude + OpenAI`: 一般是Cursor没法直接解决我们的问题，会去压榨Claude和OpenAI，Claude效果肯定是最佳的，但是因为没买会员，上下文有限，每次把它问到限额后，就会去问OpenAI，OpenAI面对不太复杂的问题还是Ok的。总的来说，代码生成的工具使用顺序是：Cursor > Claude > OpenAI
- `Kimi`: 我们正在用kimi来优化SEO，做每个页面的TDK，当然同时我们也会测试其他的大模型的效果；
- `v0.dev`：我们网站页面UI和设计方面，思路是：自己先有一个初步的想法后，通过提示词给AI工具--v0.dev来生成，通过不断优化提示词，达到最后的效果，主题也是它提供的。如果使用Next.js的，那v0真是太香了。我们另外一个用Next.js+React的项目，当时没发现v0这个工具，真是遗憾，它现在也算是宣告死亡了。