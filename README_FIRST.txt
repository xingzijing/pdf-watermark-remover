PDF 文字水印删除工具 - READ ME FIRST
====================================

这个工具用于删除 PDF 里的“文字水印”。

重要说明：
它适合删除 PDF 中真实存在的文字水印，也就是可以被鼠标选中、复制的文字。
如果水印已经变成扫描图片或背景图片的一部分，这个工具不能按文字删除，需要 OCR / 图像处理方法。


1. 先运行什么？
---------------

Windows：

1. 先运行 install_pymupdf.bat
2. 再运行 run_pdf_watermark_tool.bat

Mac：

1. 先运行 install_pymupdf_mac.command
2. 再运行 run_pdf_watermark_tool_mac.command

如果 Mac 提示没有权限打开 .command 文件，请在 Terminal 里进入这个文件夹，然后运行：

chmod +x install_pymupdf_mac.command
chmod +x run_pdf_watermark_tool_mac.command

然后再双击运行。


2. 需要什么包？
---------------

需要 Python 包：

PyMuPDF

它在 Python 里通常用下面两个名字之一导入：

fitz
pymupdf

如果你已经在 Anaconda 或自己的 Python 里安装过 PyMuPDF，一般不需要重复安装。
安装脚本只是为了帮新用户补齐依赖。


3. 基本使用步骤
---------------

1. 运行对应系统的启动文件
2. 点击 Select 选择 PDF 文件
3. 在 Watermark text 中输入要删除的水印文字
4. 在 Pages 中输入处理页码范围
5. 检查安全限制选项
6. 点击 Remove Watermark

处理完成后会生成新的 PDF，默认文件名类似：

原文件名_no_watermark.pdf

原 PDF 不会被覆盖，除非你自己把输出路径选成原文件。


4. 页码范围怎么写？
------------------

全部页面：

all

第 1 页到第 5 页：

1-5

第 3 页、第 8 页、第 10 到 12 页：

3,8,10-12

第 10 页到最后一页：

10-


5. 可以批量处理吗？
------------------

可以。

点击 Select 选择文件时，可以按住 Ctrl 或 Shift 多选 PDF。

多选时，Output 会作为输出文件夹使用。每个 PDF 会单独输出一个新文件，文件名默认是：

原文件名_no_watermark.pdf


6. 可以删除别的语言的水印吗？
----------------------------

可以。

只要水印是 PDF 里的真实文字，英文、中文、日文、韩文、德文、法文等都可以尝试。
你需要在 Watermark text 中输入对应的水印文字。

如果 PDF 生成方式比较特殊，文字可能被拆成很多片段，这种情况下可能需要尝试输入更完整或更精确的水印文字。


7. 两个重要安全选项
-------------------

建议默认保留这两个选项：

Only remove text repeated at the same position across pages

含义：
只删除在多页相同或相近位置重复出现的匹配文字。这可以降低误删正文的风险。

Only remove text inside selected page area

含义：
只删除指定页面区域内的匹配文字。
可以选择 center、top/header、bottom/footer、left、right、custom %。

如果水印是页面中间的斜向水印，建议：

1. 勾选两个安全选项
2. Area 选择 center


8. 正文里有相同文字，会不会被删？
--------------------------------

有可能。

PDF 工具看到的是“某一页某个位置有这段文字”，它不能百分百判断这段文字是正文还是水印。

为了降低误删风险，请尽量：

1. 输入完整的水印文字，不要只输入很短的词
2. 保留“相同位置重复”限制
3. 保留“指定区域”限制
4. 先用少量页码测试，例如 1-3
5. 确认效果后再处理全部页面或批量文件


9. 区域选项说明
---------------

center：
页面中间区域，适合大多数居中斜向水印。

top/header：
页面顶部区域，适合页眉水印。

bottom/footer：
页面底部区域，适合页脚水印。

left：
页面左侧区域。

right：
页面右侧区域。

custom %：
自定义区域，输入四个数字：

left top right bottom

例如：

20 20 80 80

表示只处理页面宽高 20% 到 80% 之间的中间区域。


10. 常见问题
------------

问题：提示 No module named 'fitz'

原因：
当前运行工具的 Python 没有安装 PyMuPDF。

解决：
先运行对应系统的安装脚本，或者手动运行：

python -m pip install PyMuPDF


问题：没有找到水印文字

可能原因：

1. 水印不是文字，而是图片
2. 输入的文字和 PDF 中的文字不完全一致
3. 水印文字被 PDF 拆成了多个片段
4. 安全区域选错了
5. 页码范围没有包含水印所在页面


问题：处理后看起来像没删

可能原因：

1. 水印是图片，不是文字
2. PDF 里同一水印有多层
3. 文字内容输入不完整
4. 水印位置不在当前选择区域内


11. 建议工作流程
----------------

第一次处理某类 PDF 时，不建议直接批量跑全部文件。

推荐流程：

1. 先选一个 PDF
2. 页码范围填 1-3
3. 保留两个安全选项
4. Area 选择 center
5. 输出测试文件
6. 打开测试文件检查效果
7. 确认没问题后，再处理 all 或批量处理多个文件


12. 文件说明
------------

run_pdf_watermark_tool.bat：
Windows 启动器。

install_pymupdf.bat：
Windows 安装 PyMuPDF 的辅助脚本。

run_pdf_watermark_tool_mac.command：
Mac 启动器。

install_pymupdf_mac.command：
Mac 安装 PyMuPDF 的辅助脚本。

remove_pdf_text_watermark.py：
真正执行 PDF 水印文字删除的 Python 脚本。

README_FIRST.txt：
你现在正在看的使用说明。


13. 系统支持
------------

Windows：
支持，推荐双击 run_pdf_watermark_tool.bat。

macOS：
支持，双击 run_pdf_watermark_tool_mac.command。
如果权限不足，先执行 chmod +x。
