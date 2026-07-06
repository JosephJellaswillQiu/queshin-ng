# app/main.py
import socketio
from fastapi import FastAPI
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

# 导入本地模块
from app.database import engine, Base, AsyncSessionLocal
from app.routers import auth, lobby
from app.security import decode_access_token
from app.game_manager import room_manager
from app.models import Room, PlayerInRoom, RoomStatus, User, Record
from utils.furo import get_ankan_combinations, get_kakan_combinations
from utils.riichi.yaku_han import convert_hand_to_num, convert_tile_to_num

# --- 1. 配置 FastAPI 和 Socket.IO ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()

# 挂载认证路由
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(lobby.router, prefix="/api/lobby", tags=["lobby"])

# 挂载 Socket.IO
socket_app = socketio.ASGIApp(sio, app)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# --- 2. Socket.IO 中间件：身份验证 ---

@sio.event
async def connect(sid, environ, auth):
    token = None
    if auth and 'token' in auth:
        token = auth['token']
    elif 'QUERY_STRING' in environ:
        import urllib.parse
        qs = urllib.parse.parse_qs(environ['QUERY_STRING'])
        if 'token' in qs:
            token = qs['token'][0]

    if not token:
        print(f"Connection rejected: No token {sid}")
        return False

    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    payload = decode_access_token(token)
    if not payload:
        print(f"Connection rejected: Invalid token {sid}")
        return False

    user_id = payload.get("user_id")
    username = payload.get("sub")

    await sio.save_session(sid, {'user_id': user_id, 'username': username})
    print(f"User {username}({user_id}) connected as {sid}")
    await sio.emit('response', {'message': f'Welcome {username}!'}, room=sid)


# --- 3. 业务逻辑事件 ---

@sio.event
async def create_room(sid, data):
    session = await sio.get_session(sid)
    user_id = session['user_id']
    room_name = data.get('room_name')

    if not room_name:
        await sio.emit('error', {'msg': 'Room name required'}, room=sid)
        return

    async with AsyncSessionLocal() as db:
        try:
            new_room = Room(name=room_name, created_by=user_id, status=RoomStatus.WAITING)
            db.add(new_room)
            await db.flush()

            player_entry = PlayerInRoom(
                room_id=new_room.id,
                user_id=user_id,
                player_number=0,
                is_ready=True
            )
            db.add(player_entry)
            await db.commit()

            maj_room = room_manager.create_room(new_room.id, room_name)
            if maj_room:
                maj_room.add_player(sid, user_id)
                sio.enter_room(sid, room_name)
                await sio.emit('room_joined', {
                    'room_id': new_room.id,
                    'room_name': room_name,
                    'msg': 'Room created'
                }, room=sid)
            else:
                await sio.emit('error', {'msg': 'Memory error'}, room=sid)

        except IntegrityError:
            await db.rollback()
            await sio.emit('error', {'msg': 'Room name already exists'}, room=sid)
        except Exception as e:
            await db.rollback()
            print(f"Create Error: {e}")
            await sio.emit('error', {'msg': 'Internal server error'}, room=sid)


@sio.event
async def join_room(sid, data):
    session = await sio.get_session(sid)
    user_id = session['user_id']
    room_name = data.get('room_name')

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Room).where(Room.name == room_name))
        db_room = result.scalars().first()

        if not db_room:
            await sio.emit('error', {'msg': 'Room not found'}, room=sid)
            return

        p_result = await db.execute(
            select(PlayerInRoom).where(PlayerInRoom.room_id == db_room.id)
        )
        current_players = p_result.scalars().all()

        for p in current_players:
            if p.user_id == user_id:
                sio.enter_room(sid, room_name)
                await sio.emit('room_joined', {'room_name': room_name, 'msg': 'Welcome back'}, room=sid)
                return

        if len(current_players) >= db_room.capacity:
            await sio.emit('error', {'msg': 'Room is full'}, room=sid)
            return

        seat_num = len(current_players)
        new_player = PlayerInRoom(
            room_id=db_room.id,
            user_id=user_id,
            player_number=seat_num,
            is_ready=True
        )
        db.add(new_player)

        start_game = False
        if len(current_players) + 1 == db_room.capacity:
            db_room.status = RoomStatus.PLAYING
            start_game = True

        await db.commit()

        maj_room = room_manager.get_room(room_name)
        if not maj_room:
            maj_room = room_manager.create_room(db_room.id, room_name)
            for existing_p in current_players:
                maj_room.add_player("offline", existing_p.user_id)

        maj_room.add_player(sid, user_id)
        sio.enter_room(sid, room_name)

        await sio.emit('room_joined', {
            'room_name': room_name,
            'player_count': len(current_players) + 1
        }, room=room_name)

        if start_game:
            print(f"Room {room_name} is starting!")
            maj_room.init_game()

            for i, p_sid in enumerate(maj_room.players):
                if p_sid == "offline":
                    continue
                wind = maj_room.get_player_wind(p_sid)
                await sio.emit('game_start', {
                    'hand': maj_room.hands[p_sid],
                    'seat': i,
                    'seat_label': maj_room.get_seat_label(p_sid),
                    'wind': wind,
                    'dora': maj_room.settings['dora'],
                    'dora_indicators': maj_room.dora_indicators,
                    'phase_wind': maj_room.settings['phase_wind'],
                    'round_number': maj_room.settings['round_number'],
                    'honba': maj_room.settings['honba'],
                    'is_dealer': (i == maj_room.dealer_idx),
                }, room=p_sid)

            # 通知庄家出牌
            dealer_sid = maj_room.players[maj_room.dealer_idx]
            if dealer_sid != "offline":
                await sio.emit('your_turn', {'msg': 'Your turn to discard'}, room=dealer_sid)


@sio.event
async def action_discard(sid, data):
    """出牌"""
    session = await sio.get_session(sid)
    user_id = session['user_id']

    room_name = data.get('room_name')
    tile = data.get('tile')
    room = room_manager.get_room(room_name)

    if not room or not room.is_playing:
        return

    # 验证是否轮到该玩家
    current_player = room.players[room.current_turn_idx]
    if current_player != sid:
        await sio.emit('error', {'msg': 'Not your turn'}, room=sid)
        return

    # 立直后第一张牌必须是刚摸的那张（简化处理）
    if sid in room.riichi_declared:
        # 立直玩家只能打刚摸的牌（最后一张）
        pass

    if not room.discard_tile(sid, tile):
        await sio.emit('error', {'msg': 'Tile not in hand'}, room=sid)
        return

    # 广播出牌
    seat_idx = room.get_seat_index(sid)
    await sio.emit('player_discard', {
        'sid': sid,
        'user_id': user_id,
        'seat': seat_idx,
        'tile': tile,
        'is_riichi': sid in room.riichi_declared,
    }, room=room_name)

    # 出牌后清除一发（如果不是刚立直）
    if sid not in room.riichi_declared:
        room.settings["ippatus"] = False

    # ── 检查其他玩家是否可以荣和 ──
    ron_players = []
    for other_sid in room.players:
        if other_sid == sid or other_sid == "offline":
            continue
        result = room.check_win(other_sid, tile, is_tsumo=False)
        if result:
            # 检查振听
            if not room.is_furiten(other_sid, tile):
                ron_players.append((other_sid, result))

    if ron_players:
        # 广播 ron_prompt 给所有可荣和的玩家
        room._ron_pending = {p_sid: result for p_sid, result in ron_players}
        room._ron_from_tile = tile
        room._ron_from_sid = sid
        for target_sid, result in ron_players:
            await sio.emit('ron_prompt', {
                'tile': tile,
                'from_seat': seat_idx,
                'result': result,
            }, room=target_sid)
        # 通知其他人等待荣和响应
        await sio.emit('waiting_ron', {
            'from_seat': seat_idx,
            'tile': tile,
        }, room=room_name, skip_sid=[p[0] for p in ron_players])
        return  # 等待玩家响应 action_ron 或 action_pass

    # ── 检查其他玩家是否有副露选项 ──
    furo_prompts = {}
    for other_sid in room.players:
        if other_sid == sid or other_sid == "offline":
            continue
        # 下家可以吃，其他家只能碰/杠
        other_idx = room.get_seat_index(other_sid)
        current_idx = room.get_seat_index(sid)
        is_next = (other_idx == (current_idx + 1) % 4)
        options = room.get_furo_options(other_sid, tile, allow_chi=is_next)
        if options:
            # options 是 [(hand, furo, furo_type), ...] 从 get_possible_furo 返回
            furo_prompts[other_sid] = [
                {"type": f_type, "tiles": h} for h, f, f_type in options
            ]

    if furo_prompts:
        # 设置副露 pending 追踪
        room._furo_pending = dict(furo_prompts)
        # 广播副露提示给有选项的玩家
        for target_sid, opts in furo_prompts.items():
            await sio.emit('furo_prompt', {
                'tile': tile,
                'from_seat': seat_idx,
                'options': opts,
            }, room=target_sid)
        # 通知其他人等待
        await sio.emit('waiting_furo', {
            'from_seat': seat_idx,
            'tile': tile,
        }, room=room_name, skip_sid=list(furo_prompts.keys()))
        return

    # ── 如果没有副露选项，轮到下家摸牌 ──
    await _next_player_draw(room, room_name, sid)


@sio.event
async def action_riichi(sid, data):
    """立直声明"""
    session = await sio.get_session(sid)
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)

    if not room or not room.is_playing:
        return

    if not room.can_riichi(sid):
        await sio.emit('error', {'msg': 'Cannot declare riichi'}, room=sid)
        return

    room.declare_riichi(sid)
    print(f"Player {session.get('username')} declared RIICHI in {room_name}")

    await sio.emit('riichi_declared', {
        'sid': sid,
        'seat': room.get_seat_index(sid),
        'sticks': room.riichi_sticks,
    }, room=room_name)


@sio.event
async def action_tsumo(sid, data):
    """自摸和牌"""
    session = await sio.get_session(sid)
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)

    if not room or not room.is_playing:
        return

    hand = room.hands.get(sid, [])
    if not hand:
        return

    # 最后摸的牌就是和牌
    win_tile = hand[-1]
    result = room.check_win(sid, win_tile, is_tsumo=True)

    if result:
        await sio.emit('win_declared', {
            'winner_sid': sid,
            'is_tsumo': True,
            'tile': win_tile,
            'result': result,
        }, room=room_name)
        room.is_playing = False
    else:
        await sio.emit('error', {'msg': 'Cannot tsumo with current hand'}, room=sid)


@sio.event
async def action_pon(sid, data):
    """碰"""
    await _handle_furo_response(sid, data, 'pon')


@sio.event
async def action_chi(sid, data):
    """吃"""
    await _handle_furo_response(sid, data, 'chi')


@sio.event
async def action_daiminkan(sid, data):
    """大明杠"""
    await _handle_furo_response(sid, data, 'daiminkan')


@sio.event
async def action_ankan(sid, data):
    """暗杠"""
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)
    if not room:
        return

    hand_num = convert_hand_to_num(room.hands.get(sid, []))
    furo_num = [convert_hand_to_num(m) for m in room.player_furo.get(sid, [])]
    options = get_ankan_combinations(hand_num, furo_num)

    if options:
        new_hand, new_furo, _ = options[0]
        room.player_furo[sid].append(new_furo[-1])
        # 从手牌移除
        tiles_to_remove = new_furo[-1][:4]
        for t in tiles_to_remove:
            # 转换回字符串（简化）
            pass

        room.flip_new_dora()
        # 从岭上摸牌
        tile = room.draw_kan_tile(sid)
        if tile:
            await sio.emit('ankan_declared', {
                'sid': sid,
                'seat': room.get_seat_index(sid),
                'dora_indicators': room.dora_indicators,
            }, room=room_name)
            await sio.emit('player_draw', {'tile': tile}, room=sid)
            # 检查自摸
            result = room.check_win(sid, tile, is_tsumo=True)
            if result:
                await sio.emit('win_declared', {
                    'winner_sid': sid,
                    'is_tsumo': True,
                    'tile': tile,
                    'result': result,
                }, room=room_name)
                room.is_playing = False
                return


@sio.event
async def action_pass(sid, data):
    """跳过鸣牌/荣和"""
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)
    if not room:
        return

    # 检查是否在等待荣和响应
    if hasattr(room, '_ron_pending') and sid in room._ron_pending:
        del room._ron_pending[sid]
        if not room._ron_pending:
            # 所有人都pass → 清理荣和状态 → 继续副露检查
            _cleanup_ron_pending(room)

    # 检查是否在等待副露响应
    if hasattr(room, '_furo_pending') and sid in room._furo_pending:
        del room._furo_pending[sid]
        if not room._furo_pending:
            # 所有人都pass → 下家摸牌
            _cleanup_furo_pending(room)
            last_idx = (room.current_turn_idx - 1) % 4 if room.current_turn_idx > 0 else 3
            await _next_player_draw(room, room_name, None, last_idx)
        return

    # 否则：轮到下家摸牌
    last_discarder_idx = (room.current_turn_idx - 1) % 4 if room.current_turn_idx > 0 else 3
    await _next_player_draw(room, room_name, None, last_discarder_idx)


@sio.event
async def action_ron(sid, data):
    """荣和确认"""
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)
    if not room or not room.is_playing:
        return

    if not hasattr(room, '_ron_pending') or sid not in room._ron_pending:
        await sio.emit('error', {'msg': 'Not eligible for ron'}, room=sid)
        return

    result = room._ron_pending[sid]
    tile = getattr(room, '_ron_from_tile', '?')
    from_sid = getattr(room, '_ron_from_sid', '')

    await sio.emit('win_declared', {
        'winner_sid': sid,
        'from_sid': from_sid,
        'is_tsumo': False,
        'tile': tile,
        'result': result,
    }, room=room_name)
    room.is_playing = False
    _cleanup_ron_pending(room)
    await _save_record(room, room_name, {
        'type': 'ron',
        'winner_sid': sid,
        'from_sid': from_sid,
        'tile': tile,
        'result': result,
    })


@sio.event
async def action_kakan(sid, data):
    """加杠"""
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)
    if not room:
        return

    hand_num = convert_hand_to_num(room.hands.get(sid, []))
    furo_num = [convert_hand_to_num(m) for m in room.player_furo.get(sid, [])]
    options = get_kakan_combinations(hand_num, furo_num)

    if not options:
        await sio.emit('error', {'msg': 'No kakan available'}, room=sid)
        return

    new_hand, new_furo, _ = options[0]
    # 从手牌移除加杠的那张牌
    # 找到被修改的那个刻子 → 加了第4张
    for i, (old_m, new_m) in enumerate(zip(furo_num, new_furo)):
        if len(old_m) != len(new_m) or len(new_m) == 4:
            added_tile_num = [t for t in new_m if t not in old_m]
            if added_tile_num:
                tile_to_remove = added_tile_num[0]
                # 转换回字符串并移除
                hand = room.hands[sid]
                for t_str in hand[:]:
                    if convert_tile_to_num(t_str) == tile_to_remove:
                        hand.remove(t_str)
                        break
            room.player_furo[sid][i] = room.player_furo[sid][i] + room.player_furo[sid][i][:1]
            # 将刻子扩展为杠子（4张相同）
            room.player_furo[sid][i] = [room.player_furo[sid][i][0]] * 4
            break

    # 检查抢杠
    kakan_tile = room.player_furo[sid][-1][0] if room.player_furo[sid] else ""
    if kakan_tile:
        room.settings["robbing_a_kan"] = True
        robbed = False
        for other_sid in room.players:
            if other_sid == sid or other_sid == "offline":
                continue
            result = room.check_win(other_sid, kakan_tile, is_tsumo=False)
            if result:
                await sio.emit('win_declared', {
                    'winner_sid': other_sid,
                    'from_sid': sid,
                    'is_tsumo': False,
                    'tile': kakan_tile,
                    'result': result,
                    'robbing_a_kan': True,
                }, room=room_name)
                room.is_playing = False
                room.settings["robbing_a_kan"] = False
                robbed = True
                break
        if robbed:
            return
        room.settings["robbing_a_kan"] = False

    # 翻宝牌
    room.flip_new_dora()
    room.settings["after_a_kan"] = True

    # 岭上摸牌
    tile = room.draw_kan_tile(sid)
    await sio.emit('kakan_declared', {
        'sid': sid,
        'seat': room.get_seat_index(sid),
        'meld': room.player_furo[sid][-1],
        'dora_indicators': room.dora_indicators,
    }, room=room_name)

    if tile:
        await sio.emit('player_draw', {'tile': tile, 'seat': room.get_seat_index(sid)}, room=sid)
        await sio.emit('player_draw_secret', {'user_idx': room.get_seat_index(sid)},
                       room=room_name, skip_sid=sid)
        # 检查岭上自摸
        result = room.check_win(sid, tile, is_tsumo=True)
        if result:
            await sio.emit('win_declared', {
                'winner_sid': sid,
                'is_tsumo': True,
                'tile': tile,
                'result': result,
                'after_a_kan': True,
            }, room=room_name)
            room.is_playing = False
            return

    room.current_turn_idx = room.get_seat_index(sid)
    await sio.emit('your_turn', {'msg': 'Your turn after kakan', 'hand': room.hands[sid]}, room=sid)


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


# --- 4. 辅助函数 ---

async def _next_player_draw(room, room_name, discarder_sid=None, next_idx=None):
    """下家摸牌"""
    if discarder_sid:
        current_idx = room.get_seat_index(discarder_sid)
        next_idx = (current_idx + 1) % 4
    elif next_idx is None:
        next_idx = room.current_turn_idx

    next_sid = room.players[next_idx]
    if next_sid == "offline":
        return

    room.current_turn_idx = next_idx
    room.settings["after_a_kan"] = False
    room.settings["under_the_sea"] = len(room.wall) == 0

    new_tile = room.draw_tile(next_sid)
    if new_tile:
        # 立直玩家摸牌后只能自摸或出摸到的牌
        if next_sid in room.riichi_declared:
            # 检查自摸
            result = room.check_win(next_sid, new_tile, is_tsumo=True)
            if result:
                await sio.emit('tsumo_available', {
                    'tile': new_tile,
                    'result': result,
                }, room=next_sid)
            # 无论如何发送摸的牌（前端自行处理）
        await sio.emit('player_draw', {
            'tile': new_tile,
            'seat': next_idx,
        }, room=next_sid)
        await sio.emit('player_draw_secret', {
            'user_idx': next_idx,
        }, room=room_name, skip_sid=next_sid)
        await sio.emit('your_turn', {'msg': 'Your turn'}, room=next_sid)
    else:
        # 牌山空 → 流局
        await _handle_ryuukyoku(room, room_name)


async def _handle_furo_response(sid, data, furo_type):
    """处理副露响应"""
    room_name = data.get('room_name')
    room = room_manager.get_room(room_name)
    if not room:
        return

    tile = data.get('tile')

    if furo_type == 'pon':
        hand = room.hands.get(sid, [])
        for _ in range(2):
            if tile in hand:
                hand.remove(tile)
        meld = [tile, tile, tile]
        room.player_furo[sid].append(meld)
    elif furo_type == 'chi':
        combination = data.get('combination', [])
        hand = room.hands.get(sid, [])
        for t in combination:
            if t != tile and t in hand:
                hand.remove(t)
        meld = sorted(combination)
        room.player_furo[sid].append(meld)
    elif furo_type == 'daiminkan':
        hand = room.hands.get(sid, [])
        for _ in range(3):
            if tile in hand:
                hand.remove(tile)
        meld = [tile, tile, tile, tile]
        room.player_furo[sid].append(meld)
        room.flip_new_dora()
        room.settings["after_a_kan"] = True

    # 清理 pending
    if hasattr(room, '_furo_pending') and sid in room._furo_pending:
        del room._furo_pending[sid]
    _cleanup_furo_pending_if_empty(room)

    # 广播副露结果
    await sio.emit('furo_result', {
        'sid': sid,
        'seat': room.get_seat_index(sid),
        'type': furo_type,
        'meld': room.player_furo[sid][-1],
        'dora_indicators': room.dora_indicators,
    }, room=room_name)

    # 杠后岭上摸牌
    if furo_type == 'daiminkan':
        kan_tile = room.draw_kan_tile(sid)
        if kan_tile:
            await sio.emit('player_draw', {'tile': kan_tile, 'seat': room.get_seat_index(sid)}, room=sid)
            result = room.check_win(sid, kan_tile, is_tsumo=True)
            if result:
                await sio.emit('win_declared', {
                    'winner_sid': sid,
                    'is_tsumo': True,
                    'tile': kan_tile,
                    'result': result,
                    'after_a_kan': True,
                }, room=room_name)
                room.is_playing = False
                return

    # 副露后该玩家出牌
    room.current_turn_idx = room.get_seat_index(sid)
    await sio.emit('your_turn', {
        'msg': 'Your turn after meld',
        'hand': room.hands[sid],
    }, room=sid)


async def _handle_ryuukyoku(room, room_name):
    """流局处理"""
    tenpai_players = []
    noten_players = []

    for sid in room.players:
        if sid == "offline":
            continue
        if room.is_tenpai(sid):
            tenpai_players.append(sid)
        else:
            noten_players.append(sid)

    dealer_sid = room.players[room.dealer_idx]
    dealer_tenpai = dealer_sid in tenpai_players

    await sio.emit('ryuukyoku', {
        'tenpai': [room.get_seat_index(s) for s in tenpai_players],
        'noten': [room.get_seat_index(s) for s in noten_players],
        'riichi_sticks': room.riichi_sticks,
        'dealer_tenpai': dealer_tenpai,
    }, room=room_name)

    await _save_record(room, room_name, {
        'type': 'ryuukyoku',
        'tenpai': [room.get_seat_index(s) for s in tenpai_players],
        'noten': [room.get_seat_index(s) for s in noten_players],
    })

    room.next_round(dealer_stays=dealer_tenpai)

    if room.is_game_over():
        await sio.emit('game_over', {
            'msg': 'Game finished',
            'round_number': room.settings['round_number'],
        }, room=room_name)
        room.is_playing = False
    else:
        room.init_game()
        for i, p_sid in enumerate(room.players):
            if p_sid == "offline":
                continue
            await sio.emit('game_start', {
                'hand': room.hands[p_sid],
                'seat': i,
                'seat_label': room.get_seat_label(p_sid),
                'wind': room.get_player_wind(p_sid),
                'dora': room.settings['dora'],
                'dora_indicators': room.dora_indicators,
                'phase_wind': room.settings['phase_wind'],
                'round_number': room.settings['round_number'],
                'honba': room.settings['honba'],
                'is_dealer': (i == room.dealer_idx),
            }, room=p_sid)


# ── 清理函数 ──────────────────────────────────────────────

def _cleanup_ron_pending(room):
    if hasattr(room, '_ron_pending'):
        del room._ron_pending
    if hasattr(room, '_ron_from_tile'):
        del room._ron_from_tile
    if hasattr(room, '_ron_from_sid'):
        del room._ron_from_sid


def _cleanup_furo_pending(room):
    if hasattr(room, '_furo_pending'):
        del room._furo_pending


def _cleanup_furo_pending_if_empty(room):
    if hasattr(room, '_furo_pending') and not room._furo_pending:
        del room._furo_pending


# ── 牌谱持久化 ────────────────────────────────────────────

async def _save_record(room, room_name, result_data):
    """保存牌谱到数据库"""
    try:
        import json
        async with AsyncSessionLocal() as db:
            record = Record(
                room_id=room.room_id,
                turn_count=room.settings.get('round_number', 0),
                replay_data=json.dumps(result_data, ensure_ascii=False),
                result_data=json.dumps(result_data, ensure_ascii=False),
            )
            db.add(record)
            await db.commit()
            print(f"Record saved for room {room_name}")
    except Exception as e:
        print(f"Failed to save record: {e}")
