import XCTest
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import FamilyShieldCore

final class APIClientTests: XCTestCase {
    func testAppleSignInPostsRawNonceAndOmitsBlankName() async throws {
        let transport = ScriptedTransport { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/v1/auth/apple")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body?["id_token"], "header.payload.sig")
            XCTAssertEqual(body?["nonce"], "raw-nonce-value")
            XCTAssertEqual(body?["locale"], "ko")
            XCTAssertNil(body?["display_name"])
            XCTAssertEqual(body?.count, 3)
            return HTTPResponse(status: 200, body: Data(#"{"token":"session-token","user_id":"user-1","extra":"ignored"}"#.utf8))
        }
        let client = APIClient(baseURL: "http://127.0.0.1:8000/", tokens: StaticToken(nil), transport: transport)
        let session = try await client.signInWithApple(idToken: "header.payload.sig", rawNonce: "raw-nonce-value", locale: "ko", displayName: "  ")
        XCTAssertEqual(session.token, "session-token")
        XCTAssertEqual(session.userId, "user-1")
    }

    func testAuthorizedCaseOpenAnd401SignsOut() async throws {
        let box = TokenBox("secret")
        let rejected = Rejected()
        let transport = ScriptedTransport { request in
            if request.url?.path == "/v1/cases" {
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret")
                let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
                XCTAssertEqual(body?["child_member_id"], "child-1")
                XCTAssertEqual(body?["text"], "hello")
                XCTAssertEqual(body?.count, 2)
                let json = #"{"error":"member_not_callable"}"#
                return HTTPResponse(status: 400, body: Data(json.utf8))
            }
            XCTAssertEqual(request.url?.path, "/v1/me")
            return HTTPResponse(status: 401, body: Data(#"{"detail":"Not Found"}"#.utf8))
        }
        let client = APIClient(baseURL: "http://127.0.0.1:8000", tokens: box, transport: transport) { rejected.value = $0 }
        do {
            _ = try await client.openCase(childMemberId: "child-1", text: "hello")
            XCTFail("expected member_not_callable")
        } catch let error as APIError {
            XCTAssertEqual(error, .http(status: 400, code: "member_not_callable"))
            XCTAssertNil(rejected.value)
        } catch {
            XCTFail("unexpected \(error)")
        }
        do {
            _ = try await client.me()
            XCTFail("expected 401")
        } catch let error as APIError {
            XCTAssertEqual(error, .http(status: 401, code: "http_401"))
            XCTAssertEqual(rejected.value, "secret")
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    func testParentCaseDecodesContractShape() throws {
        let json = """
        {"id":"case-1","family_id":"fam","child_member_id":"child","child_display_name":"민지",
         "state":"not_confirmed","result":"wrong","color":"yellow","answered_via":null,
         "code_channel":"static","gather":null,"parent_text":"help","transcript":null,
         "claims":{"claimed_identity":"unknown","amount":"$200","story":"  ","red_flags":["secrecy"]},
         "pattern_id":"none","timeline":["start","static_code_mismatch"],"phone_last4":"5678",
         "deadline_at":null,"created_at":"2026-11-07T00:00:00.061166+00:00",
         "updated_at":"2026-11-07T00:03:00+00:00","decided_at":"2026-11-07T00:03:00+00:00",
         "server_extra":true}
        """
        let item = try JSONCoding.decode(ParentCase.self, from: Data(json.utf8))
        XCTAssertEqual(item.childDisplayName, "민지")
        XCTAssertEqual(item.result, "wrong")
        XCTAssertEqual(item.claims?.amount, "$200")
        XCTAssertEqual(item.claims?.redFlags, ["secrecy"])
        XCTAssertNil(item.transcript)
        XCTAssertEqual(item.timeline, ["start", "static_code_mismatch"])
        let roster = try JSONCoding.decode(Roster.self, from: Data(#"{"family_id":"fam","members":[]}"#.utf8))
        XCTAssertTrue(roster.members.isEmpty)
    }

    func testEmptyBaseIsNotConfigured() async {
        let client = APIClient(baseURL: " ", tokens: StaticToken("x"), transport: ScriptedTransport { _ in
            XCTFail("no request")
            return HTTPResponse(status: 500, body: Data())
        })
        XCTAssertFalse(client.isConfigured)
        do {
            _ = try await client.nonce()
            XCTFail("expected not configured")
        } catch let error as APIError {
            XCTAssertEqual(error, .notConfigured)
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    func testPushTokenBodyUsesApnsSandbox() async throws {
        let transport = ScriptedTransport { request in
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, ["env": "sandbox", "locale": "en", "provider": "apns", "token": "abc"])
            return HTTPResponse(status: 200, body: Data(#"{"status":"registered","provider":"apns"}"#.utf8))
        }
        let client = APIClient(baseURL: "https://api.example.com", tokens: StaticToken("t"), transport: transport)
        let registered = try await client.registerPushToken(token: "abc", env: "sandbox", locale: "en")
        XCTAssertEqual(registered.provider, "apns")
    }
}

private final class StaticToken: TokenProviding, @unchecked Sendable {
    let value: String?
    init(_ value: String?) { self.value = value }
    func currentToken() -> String? { value }
}

private final class Rejected: @unchecked Sendable {
    var value: String?
}

private final class TokenBox: TokenProviding, @unchecked Sendable {
    let value: String?
    init(_ value: String?) { self.value = value }
    func currentToken() -> String? { value }
}

private final class ScriptedTransport: HTTPTransport, @unchecked Sendable {
    let handler: @Sendable (URLRequest) throws -> HTTPResponse
    init(_ handler: @escaping @Sendable (URLRequest) throws -> HTTPResponse) { self.handler = handler }
    func perform(_ request: URLRequest) async throws -> HTTPResponse { try handler(request) }
}
