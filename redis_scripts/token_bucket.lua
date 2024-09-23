local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_time = tonumber(ARGV[2])

local has_bucket = redis.call("GET", key)
if has_bucket then
    local expire_time = redis.call("PTTL", key)
    local remaining_full_refills = math.floor(expire_time / refill_time)
    local current_tokens = capacity - remaining_full_refills - 1
    if current_tokens - 1 < 0 then
        return expire_time - remaining_full_refills * refill_time
    else
        redis.call("SET", key, 1, "px", expire_time + refill_time)
        return 0
    end
else
    redis.call("SET", key, 1, "px", refill_time)
    return 0
end