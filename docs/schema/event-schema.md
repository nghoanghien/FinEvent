# Event Schema

## Mục tiêu

Định nghĩa output chuẩn cho toàn bộ project. Tất cả module extraction, validation, evaluation và demo app phải dùng cùng schema này.

Một bài báo có thể:

- Không có sự kiện: trả `events=[]` và `document_label=NO_EVENT`.
- Có một sự kiện.
- Có nhiều sự kiện liên quan đến một hoặc nhiều doanh nghiệp.

## Document-level Schema

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "document_label": "HAS_EVENT",
  "events": [],
  "warnings": [],
  "model_info": {
    "model_name": "qwen-2.5-7b-instruct",
    "prompt_version": "v1.0",
    "run_id": "20260613_001"
  }
}
```

`document_label` chỉ nhận:

- `HAS_EVENT`
- `NO_EVENT`
- `UNCERTAIN`

## Event-level Schema

```json
{
  "event_id": "cafef_hpg_20260115_001_e01",
  "ticker": "HPG",
  "company_name": "Công ty Cổ phần Tập đoàn Hòa Phát",
  "event_type": "EXPANSION",
  "event_subtype": "NEW_FACTORY",
  "event_summary": "Hòa Phát khởi công dự án nhà máy mới tại ...",
  "event_arguments": {
    "value": null,
    "location": "...",
    "partner": null,
    "project": "..."
  },
  "impact_sentiment": "POSITIVE",
  "evidence_span": "HPG khởi công dự án nhà máy...",
  "source_url": "https://example.com/news",
  "published_at": "2026-01-15T08:00:00+07:00",
  "confidence": 0.82
}
```

## Field Definitions

| Field | Type | Bắt buộc | Mô tả |
| --- | --- | --- | --- |
| `event_id` | string | Có | ID duy nhất cho event trong bài |
| `ticker` | string/null | Có | Mã cổ phiếu, null nếu không xác định được |
| `company_name` | string/null | Có | Tên doanh nghiệp |
| `event_type` | enum | Có | Nhóm sự kiện chính |
| `event_subtype` | string/null | Không | Nhãn chi tiết hơn nếu có |
| `event_summary` | string | Có | Tóm tắt ngắn sự kiện |
| `event_arguments` | object | Có | Các slot thông tin chi tiết theo từng `event_type`, ví dụ giá trị, đối tác, dự án, nhân sự, cơ quan pháp lý |
| `impact_sentiment` | enum | Có | Chiều hướng tác động: tích cực, tiêu cực, trung lập hoặc hỗn hợp |
| `evidence_span` | string | Có | Câu/đoạn trong bài làm bằng chứng |
| `source_url` | string | Có | URL bài báo |
| `published_at` | string/null | Có | Ngày đăng |
| `confidence` | number | Có | 0.0-1.0 |

## Event Type Taxonomy

| event_type | Ý nghĩa | Ví dụ |
| --- | --- | --- |
| `MA` | Mua bán, sáp nhập, thoái vốn, tái cấu trúc sở hữu | Mua lại công ty con, sáp nhập đơn vị |
| `CONTRACT` | Ký hợp đồng lớn, trúng thầu, đơn hàng lớn | Trúng gói thầu, ký hợp đồng EPC |
| `CAPITAL` | Tăng/giảm vốn, phát hành cổ phiếu/trái phiếu, mua lại cổ phiếu | Phát hành riêng lẻ, tăng vốn điều lệ |
| `LEADERSHIP` | Thay đổi lãnh đạo, HĐQT, ban điều hành | Bổ nhiệm CEO, miễn nhiệm chủ tịch |
| `EXPANSION` | Mở rộng sản xuất, nhà máy, thị trường, dự án | Khởi công nhà máy, mở chi nhánh |
| `LEGAL_RISK` | Điều tra, kiện tụng, xử phạt, tranh chấp, khủng hoảng | Bị phạt, bị điều tra |
| `PARTNERSHIP` | Hợp tác chiến lược, liên doanh, phân phối, công nghệ | Ký MOU, hợp tác với đối tác lớn |
| `LICENSE_APPROVAL` | Được cấp phép, phê duyệt, chấp thuận pháp lý | Được cấp phép dự án |
| `BUSINESS_RESULT` | Kết quả kinh doanh, doanh thu, lợi nhuận, kế hoạch/guidance | Lợi nhuận tăng mạnh, cập nhật kế hoạch năm |
| `ASSET_TRANSACTION` | Mua, bán, chuyển nhượng tài sản/dự án/công ty con | Chuyển nhượng dự án bất động sản |
| `DEBT_CREDIT` | Vay vốn, hạn mức tín dụng, trả nợ, tái cơ cấu nợ | Ký khoản vay hợp vốn, đáo hạn trái phiếu |
| `DIVIDEND_SHAREHOLDER` | Cổ tức, ESOP, giao dịch cổ đông lớn, room ngoại | Chốt quyền cổ tức tiền mặt |
| `PRODUCT_SERVICE` | Ra mắt, dừng, thu hồi, thay đổi giá sản phẩm/dịch vụ | Ra mắt dòng sản phẩm mới |
| `MARKET_LISTING` | IPO, niêm yết, hủy niêm yết, chuyển sàn, cảnh báo giao dịch | Cổ phiếu bị đưa vào diện cảnh báo |
| `ESG_OPERATIONAL_RISK` | Sự cố môi trường, an toàn lao động, gián đoạn vận hành, an ninh mạng | Nhà máy tạm dừng hoạt động do sự cố |
| `OTHER` | Có sự kiện nhưng không thuộc nhóm trên | Dùng hạn chế, phải có subtype |

## Event Subtype Taxonomy

`event_subtype` là nhãn chi tiết hơn của `event_type`. Nếu không đủ bằng chứng để chọn subtype, đặt `event_subtype=null` thay vì đoán. Nếu có subtype, giá trị phải thuộc danh sách hợp lệ của event type tương ứng.

### `MA`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `ACQUISITION` | Doanh nghiệp mua lại công ty/tài sản kinh doanh khác | mua lại, thâu tóm, hoàn tất mua |
| `MERGER` | Hai hoặc nhiều pháp nhân sáp nhập/hợp nhất | sáp nhập, hợp nhất, nhập vào |
| `DIVESTMENT` | Doanh nghiệp thoái vốn khỏi đơn vị/dự án | thoái vốn, rút vốn, bán toàn bộ phần vốn |
| `STAKE_PURCHASE` | Mua thêm cổ phần/phần vốn nhưng chưa kiểm soát toàn bộ | mua cổ phần, nâng tỷ lệ sở hữu |
| `STAKE_SALE` | Bán bớt cổ phần/phần vốn | giảm tỷ lệ sở hữu, bán cổ phần |
| `OWNERSHIP_RESTRUCTURING` | Tái cấu trúc sở hữu nội bộ hoặc chuyển quyền kiểm soát | tái cấu trúc sở hữu, chuyển công ty con |

### `CONTRACT`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `NEW_CONTRACT` | Ký hợp đồng mới có đối tác/nội dung cụ thể | ký hợp đồng, hợp đồng mới |
| `LARGE_ORDER` | Nhận đơn hàng lớn nhưng không nhấn mạnh thủ tục đấu thầu | đơn hàng lớn, đơn hàng xuất khẩu |
| `BIDDING_WIN` | Trúng thầu/gói thầu/dự án đấu thầu | trúng thầu, được chọn nhà thầu |
| `CONTRACT_EXTENSION` | Gia hạn/mở rộng hợp đồng hiện có | gia hạn hợp đồng, mở rộng phạm vi |
| `CONTRACT_TERMINATION` | Hủy/chấm dứt hợp đồng | chấm dứt hợp đồng, hủy hợp đồng |
| `EXPORT_ORDER` | Đơn hàng/hợp đồng xuất khẩu | xuất khẩu sang, đơn hàng từ nước ngoài |

### `CAPITAL`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `EQUITY_ISSUANCE` | Phát hành cổ phiếu nói chung | phát hành cổ phiếu |
| `PRIVATE_PLACEMENT` | Phát hành riêng lẻ cho nhà đầu tư cụ thể | phát hành riêng lẻ |
| `RIGHTS_OFFERING` | Chào bán cho cổ đông hiện hữu | quyền mua, cổ đông hiện hữu |
| `BONUS_SHARE` | Cổ phiếu thưởng/chia cổ tức bằng cổ phiếu | cổ phiếu thưởng, trả cổ tức bằng cổ phiếu |
| `SHARE_BUYBACK` | Mua lại cổ phiếu quỹ | mua lại cổ phiếu, cổ phiếu quỹ |
| `CAPITAL_INCREASE` | Tăng vốn điều lệ | tăng vốn điều lệ |
| `CAPITAL_REDUCTION` | Giảm vốn điều lệ | giảm vốn điều lệ |
| `BOND_ISSUANCE` | Phát hành trái phiếu | phát hành trái phiếu |

### `LEADERSHIP`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `CEO_APPOINTMENT` | Bổ nhiệm tổng giám đốc/CEO | bổ nhiệm Tổng giám đốc |
| `CEO_RESIGNATION` | CEO/tổng giám đốc từ nhiệm/miễn nhiệm | từ nhiệm, miễn nhiệm Tổng giám đốc |
| `CHAIRMAN_CHANGE` | Thay đổi chủ tịch HĐQT | bầu chủ tịch, miễn nhiệm chủ tịch |
| `BOARD_CHANGE` | Thay đổi thành viên HĐQT | thành viên HĐQT, đại hội bầu |
| `CFO_CHANGE` | Thay đổi giám đốc tài chính/kế toán trưởng nếu bài nhấn mạnh tài chính | CFO, kế toán trưởng |
| `SENIOR_MANAGEMENT_CHANGE` | Thay đổi lãnh đạo cấp cao khác | phó tổng, ban điều hành |

### `EXPANSION`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `NEW_FACTORY` | Xây/khởi công/vận hành nhà máy mới | khởi công nhà máy, nhà máy mới |
| `CAPACITY_EXPANSION` | Tăng công suất dây chuyền/nhà máy hiện hữu | nâng công suất, mở rộng dây chuyền |
| `NEW_BRANCH` | Mở chi nhánh/cửa hàng/điểm bán | mở chi nhánh, khai trương cửa hàng |
| `NEW_MARKET` | Mở thị trường mới trong/ngoài nước | mở rộng sang thị trường |
| `NEW_PROJECT` | Triển khai dự án mới chưa nhất thiết là nhà máy | dự án mới, triển khai dự án |
| `PRODUCTION_RESTART` | Khởi động lại hoạt động sản xuất/vận hành | hoạt động trở lại, tái khởi động |

### `LEGAL_RISK`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `INVESTIGATION` | Bị điều tra/thanh tra/kiểm tra chính thức | bị điều tra, thanh tra |
| `LAWSUIT` | Bị kiện hoặc tham gia vụ kiện đáng kể | khởi kiện, bị kiện |
| `ADMINISTRATIVE_FINE` | Bị xử phạt hành chính | bị phạt, quyết định xử phạt |
| `REGULATORY_WARNING` | Bị nhắc nhở/cảnh báo từ cơ quan quản lý | cảnh báo, nhắc nhở, yêu cầu giải trình |
| `CRIMINAL_CASE` | Liên quan vụ án hình sự | khởi tố, bắt tạm giam |
| `CUSTOMER_SUPPLIER_DISPUTE` | Tranh chấp với khách hàng/nhà cung cấp/đối tác | tranh chấp, khiếu nại |

### `PARTNERSHIP`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `STRATEGIC_PARTNERSHIP` | Hợp tác chiến lược quy mô dài hạn | hợp tác chiến lược |
| `JOINT_VENTURE` | Thành lập liên doanh/công ty chung | liên doanh, góp vốn thành lập |
| `MOU_SIGNING` | Ký biên bản ghi nhớ/chưa phải hợp đồng chính thức | MOU, biên bản ghi nhớ |
| `DISTRIBUTION_PARTNERSHIP` | Hợp tác phân phối/bán hàng/kênh đại lý | phân phối độc quyền, đại lý |
| `TECHNOLOGY_PARTNERSHIP` | Hợp tác công nghệ/chuyển giao kỹ thuật | chuyển giao công nghệ, nền tảng công nghệ |

### `LICENSE_APPROVAL`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `PROJECT_APPROVAL` | Dự án được phê duyệt/chấp thuận | phê duyệt dự án, chấp thuận chủ trương |
| `INVESTMENT_APPROVAL` | Được chấp thuận đầu tư/góp vốn/mở rộng đầu tư | chấp thuận đầu tư |
| `LICENSE_GRANTED` | Được cấp giấy phép/giấy chứng nhận | được cấp phép, giấy phép |
| `LICENSE_RENEWAL` | Gia hạn giấy phép | gia hạn giấy phép |
| `REGULATORY_CLEARANCE` | Được cơ quan quản lý thông qua điều kiện pháp lý | thông qua, chấp thuận từ cơ quan |

### `BUSINESS_RESULT`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `REVENUE_GROWTH` | Doanh thu tăng đáng chú ý | doanh thu tăng |
| `PROFIT_GROWTH` | Lợi nhuận tăng đáng chú ý | lợi nhuận tăng, lãi tăng |
| `PROFIT_DECLINE` | Lợi nhuận giảm đáng chú ý | lợi nhuận giảm, lãi giảm |
| `LOSS_REPORT` | Báo lỗ hoặc lỗ tăng mạnh | báo lỗ, lỗ ròng |
| `GUIDANCE_UPDATE` | Cập nhật kế hoạch/guidance kinh doanh | điều chỉnh kế hoạch, đặt mục tiêu |
| `BACKLOG_UPDATE` | Công bố backlog/giá trị hợp đồng chưa thực hiện | backlog, giá trị đơn hàng tồn |

### `ASSET_TRANSACTION`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `ASSET_PURCHASE` | Mua tài sản/dự án/nhà máy/quỹ đất | mua tài sản, nhận chuyển nhượng |
| `ASSET_SALE` | Bán tài sản lớn | bán tài sản, thanh lý |
| `PROJECT_TRANSFER` | Chuyển nhượng dự án | chuyển nhượng dự án |
| `LAND_USE_RIGHT_TRANSFER` | Chuyển nhượng quyền sử dụng đất/quỹ đất | quyền sử dụng đất, quỹ đất |
| `SUBSIDIARY_TRANSFER` | Chuyển nhượng công ty con/công ty liên kết | chuyển nhượng công ty con |

### `DEBT_CREDIT`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `NEW_LOAN` | Ký khoản vay mới | khoản vay, vay vốn |
| `CREDIT_FACILITY` | Được cấp hạn mức tín dụng | hạn mức tín dụng |
| `DEBT_RESTRUCTURING` | Gia hạn/tái cơ cấu nợ | tái cơ cấu nợ, gia hạn nợ |
| `DEBT_DEFAULT_RISK` | Rủi ro chậm trả/vỡ nợ | chậm trả, không thanh toán đúng hạn |
| `BOND_REPAYMENT` | Thanh toán/mua lại trái phiếu đến hạn | trả nợ trái phiếu, mua lại trái phiếu |
| `CREDIT_RATING_CHANGE` | Thay đổi xếp hạng tín nhiệm | nâng/hạ xếp hạng tín nhiệm |

### `DIVIDEND_SHAREHOLDER`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `CASH_DIVIDEND` | Trả cổ tức bằng tiền | cổ tức tiền mặt |
| `STOCK_DIVIDEND` | Trả cổ tức bằng cổ phiếu | cổ tức bằng cổ phiếu |
| `ESOP` | Phát hành cổ phiếu ESOP | ESOP |
| `MAJOR_SHAREHOLDER_TRANSACTION` | Cổ đông lớn/nội bộ mua bán đáng kể | cổ đông lớn mua/bán |
| `FOREIGN_ROOM_CHANGE` | Thay đổi tỷ lệ sở hữu nước ngoài/room ngoại | room ngoại, tỷ lệ sở hữu nước ngoài |

### `PRODUCT_SERVICE`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `NEW_PRODUCT_LAUNCH` | Ra mắt sản phẩm mới | ra mắt sản phẩm |
| `NEW_SERVICE_LAUNCH` | Ra mắt dịch vụ/nền tảng mới | ra mắt dịch vụ |
| `PRODUCT_DISCONTINUATION` | Dừng sản phẩm/dịch vụ | dừng kinh doanh, ngừng sản phẩm |
| `PRODUCT_RECALL` | Thu hồi sản phẩm | thu hồi sản phẩm |
| `PRICE_CHANGE` | Thay đổi giá bán đáng chú ý | tăng giá, giảm giá |

### `MARKET_LISTING`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `IPO` | Chào bán lần đầu ra công chúng | IPO |
| `LISTING` | Niêm yết/giao dịch mới trên sàn | niêm yết, giao dịch trên HOSE/HNX/UPCoM |
| `DELISTING` | Hủy niêm yết | hủy niêm yết |
| `EXCHANGE_TRANSFER` | Chuyển sàn giao dịch | chuyển sàn |
| `TRADING_WARNING` | Bị cảnh báo/kiểm soát/hạn chế giao dịch | diện cảnh báo, kiểm soát |
| `TRADING_SUSPENSION` | Tạm ngừng/đình chỉ giao dịch | đình chỉ giao dịch, tạm ngừng giao dịch |

### `ESG_OPERATIONAL_RISK`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `ENVIRONMENTAL_INCIDENT` | Sự cố môi trường | ô nhiễm, sự cố môi trường |
| `WORKPLACE_ACCIDENT` | Tai nạn lao động/an toàn nhà máy | tai nạn lao động |
| `SUPPLY_CHAIN_DISRUPTION` | Gián đoạn chuỗi cung ứng | thiếu nguyên liệu, đứt gãy nguồn cung |
| `FACTORY_SHUTDOWN` | Nhà máy/dự án tạm dừng vận hành | dừng hoạt động, tạm ngừng sản xuất |
| `CYBER_SECURITY_INCIDENT` | Sự cố an ninh mạng/dữ liệu | tấn công mạng, rò rỉ dữ liệu |

### `OTHER`

| event_subtype | Khi dùng | Ví dụ tín hiệu trong bài |
| --- | --- | --- |
| `OTHER_SPECIFIC_EVENT` | Có sự kiện doanh nghiệp cụ thể nhưng taxonomy v1 chưa bao phủ | phải ghi rõ lý do trong `event_summary` |

## Impact Sentiment

| impact_sentiment | Ý nghĩa |
| --- | --- |
| `POSITIVE` | Sự kiện có khả năng tốt cho doanh nghiệp |
| `NEGATIVE` | Sự kiện có khả năng bất lợi |
| `NEUTRAL` | Tác động chưa rõ hoặc cân bằng |
| `MIXED` | Có cả tác động tích cực và tiêu cực |

## Event Arguments

`event_arguments` là object chứa các slot chi tiết của sự kiện. Mục tiêu của field này là giữ lại thông tin quan trọng để người dùng không chỉ biết "sự kiện thuộc loại gì", mà còn biết sự kiện xảy ra với ai, ở đâu, giá trị bao nhiêu, thời điểm nào và bằng chứng nào hỗ trợ.

Nguyên tắc chung:

- Chỉ điền argument nếu thông tin có trong bài báo hoặc metadata đầu vào.
- Nếu không có bằng chứng, bỏ key hoặc đặt `null`; không được đoán.
- Giữ số liệu theo dạng text gốc nếu chưa có bước chuẩn hóa riêng, ví dụ `"500 tỷ đồng"`, `"15%"`, `"quý II/2026"`.
- Dùng `snake_case` cho tên key.
- `event_arguments` có thể là `{}` nếu bài báo có sự kiện rõ nhưng không có slot chi tiết ngoài summary/evidence.

### Common Argument Fields

Các key dưới đây có thể dùng cho nhiều event type:

| Key | Ý nghĩa | Ví dụ |
| --- | --- | --- |
| `value` | Giá trị chung nếu bài chỉ nêu một con số quan trọng | `"500 tỷ đồng"` |
| `currency` | Đơn vị tiền tệ nếu tách được | `"VND"`, `"USD"` |
| `percentage` | Tỷ lệ phần trăm quan trọng | `"15%"` |
| `quantity` | Số lượng chung | `"20 triệu cổ phiếu"` |
| `time` | Thời điểm được nhắc trong bài | `"quý II/2026"` |
| `effective_date` | Ngày hiệu lực/chốt quyền/bắt đầu áp dụng | `"2026-07-01"` |
| `partner` | Đối tác, khách hàng, nhà cung cấp, bên liên quan | `"Tập đoàn A"` |
| `project` | Tên dự án/gói thầu/công trình | `"Dự án cao tốc ..."` |
| `location` | Địa điểm liên quan | `"Bình Dương"` |
| `product` | Sản phẩm/dịch vụ liên quan | `"thép xây dựng"` |
| `person` | Tên cá nhân liên quan | `"Nguyễn Văn A"` |
| `role` | Chức danh/vai trò của cá nhân | `"Tổng giám đốc"` |
| `legal_authority` | Cơ quan quản lý/tòa án/cơ quan cấp phép | `"Ủy ban Chứng khoán Nhà nước"` |
| `document_reference` | Số quyết định/nghị quyết/thông báo nếu có | `"Quyết định số ..."` |
| `transaction_status` | Trạng thái giao dịch/sự kiện | `"đã hoàn tất"`, `"dự kiến"`, `"được chấp thuận"` |

### Argument Fields Theo Event Type

#### `MA`

| Key | Ý nghĩa |
| --- | --- |
| `buyer` | Bên mua/thâu tóm |
| `seller` | Bên bán/chuyển nhượng |
| `target_company` | Công ty/tài sản mục tiêu |
| `stake_percentage` | Tỷ lệ cổ phần/phần vốn mua bán |
| `transaction_value` | Giá trị thương vụ |
| `ownership_before` | Tỷ lệ sở hữu trước giao dịch |
| `ownership_after` | Tỷ lệ sở hữu sau giao dịch |
| `transaction_status` | Dự kiến/đã ký/đã hoàn tất/được phê duyệt |

Ví dụ:

```json
{
  "buyer": "Công ty A",
  "seller": "Công ty B",
  "target_company": "Công ty C",
  "stake_percentage": "51%",
  "transaction_value": "1.200 tỷ đồng",
  "transaction_status": "đã ký thỏa thuận"
}
```

#### `CONTRACT`

| Key | Ý nghĩa |
| --- | --- |
| `partner` | Khách hàng/chủ đầu tư/đối tác ký hợp đồng |
| `contract_value` | Giá trị hợp đồng/gói thầu |
| `package_name` | Tên gói thầu |
| `project` | Dự án liên quan |
| `product` | Hàng hóa/dịch vụ cung cấp |
| `contract_duration` | Thời hạn hợp đồng |
| `delivery_market` | Thị trường/khu vực giao hàng |

Ví dụ:

```json
{
  "partner": "Chủ đầu tư A",
  "contract_value": "500 tỷ đồng",
  "package_name": "Gói thầu EPC ...",
  "project": "Dự án điện gió ...",
  "product": "thiết bị cơ điện",
  "contract_duration": "18 tháng"
}
```

#### `CAPITAL`

| Key | Ý nghĩa |
| --- | --- |
| `capital_before` | Vốn điều lệ trước thay đổi |
| `capital_after` | Vốn điều lệ sau thay đổi |
| `share_volume` | Số lượng cổ phiếu phát hành/mua lại |
| `issue_price` | Giá phát hành |
| `offering_method` | Phương thức phát hành/chào bán |
| `target_investors` | Nhà đầu tư mục tiêu nếu phát hành riêng lẻ |
| `use_of_proceeds` | Mục đích sử dụng vốn |
| `bond_value` | Giá trị trái phiếu phát hành |
| `maturity` | Kỳ hạn trái phiếu/khoản vốn |
| `interest_rate` | Lãi suất nếu có |

Ví dụ:

```json
{
  "share_volume": "100 triệu cổ phiếu",
  "issue_price": "10.000 đồng/cổ phiếu",
  "offering_method": "phát hành riêng lẻ",
  "capital_before": "3.000 tỷ đồng",
  "capital_after": "4.000 tỷ đồng",
  "use_of_proceeds": "bổ sung vốn cho dự án ..."
}
```

#### `LEADERSHIP`

| Key | Ý nghĩa |
| --- | --- |
| `person` | Người được bổ nhiệm/từ nhiệm/miễn nhiệm |
| `role` | Chức danh liên quan |
| `action` | Bổ nhiệm, miễn nhiệm, từ nhiệm, bầu mới |
| `predecessor` | Người tiền nhiệm nếu có |
| `successor` | Người kế nhiệm nếu có |
| `effective_date` | Ngày hiệu lực |
| `term` | Nhiệm kỳ |

#### `EXPANSION`

| Key | Ý nghĩa |
| --- | --- |
| `project` | Dự án/nhà máy/chi nhánh mới |
| `location` | Địa điểm mở rộng |
| `investment_value` | Tổng vốn đầu tư |
| `capacity` | Công suất/quy mô tăng thêm |
| `start_date` | Thời điểm khởi công/bắt đầu |
| `operation_date` | Thời điểm vận hành dự kiến |
| `product` | Sản phẩm/dịch vụ liên quan |
| `market` | Thị trường mới |

#### `LEGAL_RISK`

| Key | Ý nghĩa |
| --- | --- |
| `legal_authority` | Cơ quan điều tra/xử phạt/tòa án |
| `violation` | Hành vi vi phạm/vấn đề pháp lý |
| `penalty_value` | Số tiền phạt/bồi thường |
| `case_name` | Tên vụ án/vụ kiện nếu có |
| `affected_party` | Bên bị ảnh hưởng hoặc bên tranh chấp |
| `decision_date` | Ngày quyết định/thông báo |
| `remediation` | Biện pháp khắc phục nếu bài nêu |

Ví dụ:

```json
{
  "legal_authority": "Ủy ban Chứng khoán Nhà nước",
  "violation": "công bố thông tin không đúng thời hạn",
  "penalty_value": "120 triệu đồng",
  "decision_date": "2026-05-20"
}
```

#### `PARTNERSHIP`

| Key | Ý nghĩa |
| --- | --- |
| `partner` | Đối tác hợp tác |
| `agreement_type` | MOU, hợp tác chiến lược, liên doanh, phân phối |
| `partnership_scope` | Phạm vi hợp tác |
| `project` | Dự án/chương trình hợp tác |
| `duration` | Thời hạn hợp tác |
| `expected_goal` | Mục tiêu hợp tác được nêu trong bài |

#### `LICENSE_APPROVAL`

| Key | Ý nghĩa |
| --- | --- |
| `legal_authority` | Cơ quan cấp phép/phê duyệt |
| `approval_type` | Loại phê duyệt/chấp thuận |
| `project` | Dự án được phê duyệt |
| `license_id` | Số giấy phép/quyết định |
| `location` | Địa điểm dự án |
| `approved_area` | Diện tích/quy mô được phê duyệt |
| `effective_date` | Ngày hiệu lực |

#### `BUSINESS_RESULT`

| Key | Ý nghĩa |
| --- | --- |
| `period` | Kỳ báo cáo |
| `revenue` | Doanh thu |
| `profit` | Lợi nhuận |
| `growth_rate` | Tỷ lệ tăng/giảm |
| `plan_completion` | Mức hoàn thành kế hoạch |
| `cause` | Nguyên nhân chính nếu bài nêu |
| `guidance` | Kế hoạch/guidance mới |

#### `ASSET_TRANSACTION`

| Key | Ý nghĩa |
| --- | --- |
| `asset_name` | Tên tài sản/dự án/công ty con |
| `asset_type` | Loại tài sản: dự án, nhà máy, quỹ đất, công ty con |
| `buyer` | Bên mua/nhận chuyển nhượng |
| `seller` | Bên bán/chuyển nhượng |
| `transaction_value` | Giá trị giao dịch |
| `ownership_change` | Tỷ lệ/quyền sở hữu thay đổi |
| `transaction_status` | Trạng thái giao dịch |

#### `DEBT_CREDIT`

| Key | Ý nghĩa |
| --- | --- |
| `lender` | Ngân hàng/chủ nợ/trái chủ |
| `borrower` | Bên vay/phát hành |
| `loan_value` | Giá trị khoản vay |
| `credit_limit` | Hạn mức tín dụng |
| `bond_code` | Mã trái phiếu |
| `maturity` | Kỳ hạn/ngày đáo hạn |
| `interest_rate` | Lãi suất |
| `repayment_status` | Đã trả/chậm trả/tái cơ cấu |
| `collateral` | Tài sản bảo đảm nếu có |

#### `DIVIDEND_SHAREHOLDER`

| Key | Ý nghĩa |
| --- | --- |
| `dividend_type` | Tiền mặt/cổ phiếu |
| `dividend_rate` | Tỷ lệ cổ tức |
| `record_date` | Ngày đăng ký cuối cùng |
| `payment_date` | Ngày thanh toán |
| `shareholder` | Cổ đông/cổ đông lớn liên quan |
| `transaction_volume` | Khối lượng mua/bán |
| `ownership_before` | Tỷ lệ sở hữu trước giao dịch |
| `ownership_after` | Tỷ lệ sở hữu sau giao dịch |

#### `PRODUCT_SERVICE`

| Key | Ý nghĩa |
| --- | --- |
| `product` | Sản phẩm/dịch vụ |
| `launch_date` | Thời điểm ra mắt |
| `market` | Thị trường/kênh bán |
| `price_change` | Mức tăng/giảm giá |
| `affected_customers` | Nhóm khách hàng bị ảnh hưởng |
| `reason` | Lý do ra mắt/dừng/thu hồi/thay đổi giá |

#### `MARKET_LISTING`

| Key | Ý nghĩa |
| --- | --- |
| `exchange` | Sàn giao dịch |
| `ticker` | Mã chứng khoán |
| `listing_date` | Ngày niêm yết/giao dịch |
| `status` | Niêm yết, hủy niêm yết, cảnh báo, đình chỉ |
| `reason` | Lý do bị cảnh báo/hủy niêm yết/đình chỉ |
| `affected_shares` | Số lượng cổ phiếu bị ảnh hưởng |

#### `ESG_OPERATIONAL_RISK`

| Key | Ý nghĩa |
| --- | --- |
| `incident_type` | Loại sự cố |
| `location` | Địa điểm xảy ra |
| `time` | Thời điểm xảy ra |
| `impact_scope` | Phạm vi ảnh hưởng được bài nêu |
| `legal_authority` | Cơ quan liên quan nếu có |
| `remediation` | Biện pháp khắc phục |
| `downtime` | Thời gian dừng vận hành nếu có |

#### `OTHER`

| Key | Ý nghĩa |
| --- | --- |
| `custom_arguments` | Object chứa slot riêng nếu taxonomy chưa bao phủ |
| `reason_for_other` | Lý do không map được vào event type khác |

Chỉ dùng `OTHER` khi có sự kiện doanh nghiệp cụ thể và không thể map hợp lý vào taxonomy v1.

## Quy tắc validate

1. `event_type` và `impact_sentiment` phải thuộc enum.
2. Nếu `event_subtype` khác `null`, subtype phải thuộc danh sách hợp lệ của `event_type`.
3. `evidence_span` phải là đoạn có trong `text` hoặc gần khớp với văn bản gốc.
4. Nếu `document_label=NO_EVENT`, `events` phải là mảng rỗng.
5. Nếu `document_label=HAS_EVENT`, `events` phải có ít nhất 1 record.
6. `confidence` nằm trong khoảng 0.0 đến 1.0.
7. Không được sinh ticker nếu không có bằng chứng hoặc mapping đủ tin cậy.
8. `event_summary` không được chứa thông tin ngoài bài báo.
9. `event_arguments` chỉ chứa thông tin có bằng chứng trong bài hoặc metadata đầu vào.
10. Các key trong `event_arguments` nên ưu tiên đúng nhóm field của `event_type`; nếu cần field ngoài danh sách, dùng key rõ nghĩa và vẫn phải có evidence.
11. Với số tiền, tỷ lệ, ngày tháng, số lượng, giữ nguyên dạng text gốc nếu chưa có bước chuẩn hóa riêng.
12. Không dùng `event_arguments` để lặp lại toàn bộ `event_summary`; chỉ lưu các slot có thể tái sử dụng cho phân tích/bảng dữ liệu.

## Cấu trúc nhãn cho thí nghiệm

### Label Schema A: Flat Event Type

Một event có đúng một `event_type`.

Ví dụ:

```json
{
  "event_type": "CONTRACT"
}
```

Ưu điểm: dễ đánh giá, dễ giải thích.

Nhược điểm: khó biểu diễn sự kiện phức hợp.

### Label Schema B: Hierarchical Event Type

Gồm `event_type` và `event_subtype`.

Ví dụ:

```json
{
  "event_type": "CAPITAL",
  "event_subtype": "BOND_ISSUANCE"
}
```

Subtype phải lấy từ `Event Subtype Taxonomy`. Một số ví dụ hợp lệ:

| event_type | event_subtype | Ý nghĩa |
| --- | --- | --- |
| `CONTRACT` | `BIDDING_WIN` | Doanh nghiệp trúng gói thầu/dự án |
| `CAPITAL` | `BOND_ISSUANCE` | Doanh nghiệp phát hành trái phiếu |
| `LEADERSHIP` | `CEO_APPOINTMENT` | Bổ nhiệm tổng giám đốc/CEO |
| `EXPANSION` | `NEW_FACTORY` | Mở hoặc khởi công nhà máy mới |
| `LEGAL_RISK` | `ADMINISTRATIVE_FINE` | Bị xử phạt hành chính |
| `LICENSE_APPROVAL` | `PROJECT_APPROVAL` | Dự án được chấp thuận/phê duyệt |
| `MARKET_LISTING` | `TRADING_WARNING` | Cổ phiếu bị cảnh báo/kiểm soát giao dịch |

Ưu điểm: giàu thông tin hơn và giúp phân tích lỗi rõ hơn.

Nhược điểm: cần nhiều dữ liệu hơn cho subtype.

Quy tắc fallback: nếu xác định được `event_type` nhưng không đủ bằng chứng chọn subtype, đặt `event_subtype=null`; không dùng subtype gần đúng theo cảm tính.

### Label Schema C: Multi-label Attributes

Biểu diễn tính chất sự kiện bằng vector nhị phân 8 chiều. Đây là schema dùng cho thí nghiệm multi-label, chưa bắt buộc trong output production v1.

```json
{
  "event_attributes": {
    "financial": 1,
    "governance": 0,
    "legal": 0,
    "operation": 0,
    "market": 1,
    "strategic": 0,
    "capital_market": 0,
    "risk": 0
  }
}
```

Các chiều nhãn:

| Attribute | Ý nghĩa | Ví dụ bật `1` |
| --- | --- | --- |
| `financial` | Liên quan doanh thu, lợi nhuận, dòng tiền, nợ, vốn | kết quả kinh doanh, phát hành vốn, vay vốn |
| `governance` | Liên quan lãnh đạo, HĐQT, cổ đông, quản trị | bổ nhiệm CEO, cổ đông lớn bán cổ phần |
| `legal` | Liên quan pháp lý, cấp phép, kiện tụng, xử phạt | được cấp phép dự án, bị phạt |
| `operation` | Liên quan sản xuất, nhà máy, dự án, vận hành | mở nhà máy, dừng sản xuất |
| `market` | Liên quan thị trường, khách hàng, xuất khẩu, sản phẩm | đơn hàng xuất khẩu, ra mắt sản phẩm |
| `strategic` | Liên quan M&A, hợp tác chiến lược, đầu tư dài hạn | sáp nhập, liên doanh, hợp tác chiến lược |
| `capital_market` | Liên quan cổ phiếu, trái phiếu, niêm yết, cổ tức | IPO, cổ tức, trái phiếu |
| `risk` | Sự kiện mang rủi ro bất lợi hoặc bất định cao | kiện tụng, bị điều tra, dừng nhà máy |

Rule mapping gợi ý theo `event_type`:

| event_type | Attributes thường bật |
| --- | --- |
| `MA` | `strategic=1`, `financial=1`, `governance=1` nếu đổi sở hữu/quyền kiểm soát |
| `CONTRACT` | `financial=1`, `market=1`, thêm `operation=1` nếu liên quan cung ứng/sản xuất |
| `CAPITAL` | `financial=1`, `capital_market=1` |
| `LEADERSHIP` | `governance=1` |
| `EXPANSION` | `operation=1`, `strategic=1`, thêm `market=1` nếu mở thị trường/kênh bán |
| `LEGAL_RISK` | `legal=1`, `risk=1` |
| `PARTNERSHIP` | `strategic=1`, thêm `market=1` hoặc `operation=1` tùy nội dung hợp tác |
| `LICENSE_APPROVAL` | `legal=1`, `operation=1` |
| `BUSINESS_RESULT` | `financial=1` |
| `ASSET_TRANSACTION` | `financial=1`, `strategic=1`, thêm `operation=1` nếu tài sản phục vụ vận hành |
| `DEBT_CREDIT` | `financial=1`, thêm `risk=1` nếu có dấu hiệu chậm trả/vỡ nợ |
| `DIVIDEND_SHAREHOLDER` | `financial=1`, `governance=1`, `capital_market=1` |
| `PRODUCT_SERVICE` | `market=1`, thêm `operation=1` nếu liên quan sản xuất/cung ứng |
| `MARKET_LISTING` | `capital_market=1`, `governance=1` |
| `ESG_OPERATIONAL_RISK` | `operation=1`, `risk=1`, thêm `legal=1` nếu có cơ quan quản lý/xử phạt |

Ví dụ 1: doanh nghiệp trúng thầu dự án lớn.

```json
{
  "event_type": "CONTRACT",
  "event_subtype": "BIDDING_WIN",
  "event_attributes": {
    "financial": 1,
    "governance": 0,
    "legal": 0,
    "operation": 1,
    "market": 1,
    "strategic": 0,
    "capital_market": 0,
    "risk": 0
  }
}
```

Ví dụ 2: doanh nghiệp bị xử phạt hành chính.

```json
{
  "event_type": "LEGAL_RISK",
  "event_subtype": "ADMINISTRATIVE_FINE",
  "event_attributes": {
    "financial": 0,
    "governance": 0,
    "legal": 1,
    "operation": 0,
    "market": 0,
    "strategic": 0,
    "capital_market": 0,
    "risk": 1
  }
}
```

Ví dụ 3: doanh nghiệp phát hành trái phiếu.

```json
{
  "event_type": "CAPITAL",
  "event_subtype": "BOND_ISSUANCE",
  "event_attributes": {
    "financial": 1,
    "governance": 0,
    "legal": 0,
    "operation": 0,
    "market": 0,
    "strategic": 0,
    "capital_market": 1,
    "risk": 0
  }
}
```

Ưu điểm: phù hợp sự kiện đa khía cạnh và giúp đánh giá theo nhiều chiều thông tin.

Nhược điểm: đánh giá phức tạp hơn, cần metric như micro/macro-F1 và Hamming loss.

## Ví dụ output hoàn chỉnh

```json
{
  "article_id": "vietstock_vhm_20260201_003",
  "document_label": "HAS_EVENT",
  "events": [
    {
      "event_id": "vietstock_vhm_20260201_003_e01",
      "ticker": "VHM",
      "company_name": "Vinhomes",
      "event_type": "LICENSE_APPROVAL",
      "event_subtype": "PROJECT_APPROVAL",
      "event_summary": "Vinhomes được chấp thuận triển khai một dự án khu đô thị mới.",
      "event_arguments": {
        "project": "Dự án khu đô thị ...",
        "location": "...",
        "value": null
      },
      "impact_sentiment": "POSITIVE",
      "evidence_span": "Vinhomes vừa được chấp thuận chủ trương đầu tư dự án...",
      "source_url": "https://example.com/article",
      "published_at": "2026-02-01T09:30:00+07:00",
      "confidence": 0.86
    }
  ],
  "warnings": [],
  "model_info": {
    "model_name": "qwen-2.5-7b-instruct",
    "prompt_version": "v1.0",
    "run_id": "20260613_001"
  }
}
```
