# 插件装不上？先跑这个骨架

这不是教程，是一个**对照组**。

你怀疑自己的插件写错了，但你分不清到底是代码错、环境错、还是加载位置错。
那就先跑这个骨架：它只有 26 行、零依赖、免构建。它跑通，说明环境没问题；它也不通，说明先修环境（见 [docs/01](../docs/01-插件不加载.md)）。

## 装法（两条路，选你有的那条）

### A. 有 DSH 插件注入器

```
dev_inject_plugin  <这个 starter 目录的绝对路径>
```

然后看 `dev_plugin_status`：状态是 `[active]` 且工具列表里出现 `ping`，就成了。

### B. 没有注入器：手动链接

1. 在**你正在跑的那个** profile 的 `node_modules` 下建一个目录链接：

   ```
   mklink /J "C:\Users\<你>\.dsh\profiles\desktop\node_modules\dsh-plugin-starter" "<这个 starter 的绝对路径>"
   ```

   注意是 desktop 还是 web，链错房间等于没链（这也是 docs/01 原因 B）。

2. 在同一个 profile 的 `cordis.patch.yml` 末尾追加：

   ```yaml
   - insert:
       - id: dsh-plugin-starter
         name: dsh-plugin-starter
   ```

3. 重启 DSH。

## 验证

对它说一句「ping 一下」，或者直接调 `ping` 工具。返回 `pong, 世界` 就算通。

**不通别改代码，先看日志。** 顺带确认 `ping` 在别的会话里也出现——只在一个会话里有，那是加载位置的问题，不是工具注册的问题。

## 跑通之后

把你的逻辑往 `apply` 里加，一次加一件，加一次验一次。
别一次加五个服务，然后花一晚上找哪一个是凶手——我干过。
