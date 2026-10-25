export const name = 'dsh-plugin-starter'

// 关键：不要写 `export const inject = ['tools']`。
// 那会让插件在「拿不到 tools」的作用域里整块静默不加载（见 docs/01）。
// ctx.inject 是「等这个服务出现再跑」，根上下文和预设树里都能用。
export function apply(ctx) {
  ctx.inject(['tools'], (ctx) => {
    ctx.effect(() => ctx.tools.register({
      name: 'ping',
      description: '验证骨架跑通没有：返回一句 pong。',
      parameters: {
        type: 'object',
        properties: {
          who: { type: 'string', description: '对谁说，缺省是「世界」' },
        },
        additionalProperties: false,
      },
      output: {
        schema: { type: 'string' },
        render: (_args, value) => [{ type: 'text', text: String(value) }],
      },
      async execute(args) {
        return `pong, ${args?.who || '世界'}`
      },
    }), 'ping tool')
  })
}
